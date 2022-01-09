# Main.py

import os
import cv2
import argparse
import Deteksi_Karakter 
import Deteksi_Plat 
import imutils
import Calibration as cal
import Preprocessing_Citra as pp
import csv
from csv import writer
import gate

# Modul warna RGB
SCALAR_BLACK = (0.0, 0.0, 0.0)
SCALAR_WHITE = (255.0, 255.0, 255.0)
SCALAR_YELLOW = (0.0, 255.0, 255.0)
SCALAR_GREEN = (0.0, 255.0, 0.0)
SCALAR_RED = (0.0, 0.0, 255.0)
N_VERIFY = 7 

MIN_CONTOUR_AREA = 100
RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30

table="information.xlsx"
db=[]
header = []

class ContourWithData:
    npaContour = None
    boundingRect = None
    intRectX = 0
    intRectY = 0
    intRectWidth = 0
    intRectHeight = 0
    fltArea = 0.0

    def calculateRectTopLeftPointAndWidthAndHeight(self):
        [intX, intY, intWidth, intHeight] = self.boundingRect
        self.intRectX = intX
        self.intRectY = intY
        self.intRectWidth = intWidth
        self.intRectHeight = intHeight

    def checkIfContourIsValid(self):
        if self.fltArea < MIN_CONTOUR_AREA: return False
        return True

showSteps = False

def main():


    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video", help="Path to video file")

    args = vars(ap.parse_args())

    #Perubahan
    camera = cv2.VideoCapture(0) 
    loop = True

    # Load and check KNN Model
    assert Deteksi_Karakter.loadKNNDataAndTrainKNN(), "KNN can't be loaded !"
    save_number = 0
    old_license= ""
    licenses_verify = []

    # Looping for Video
    while loop:
        # grab the current frame
        (grabbed, frame) = camera.read()
        if args.get("video") and not grabbed:
            break

        # resize the frame and preprocess
        ori_img = imutils.resize(frame, width=620)
        _, img_thresh = pp.preprocess(ori_img)

        # Show the preprocess result
        cv2.imshow("threshold", img_thresh)

        # Get the license in frame
        ori_img = imutils.transform(ori_img)

        # get_plate(ori_img)
        Plate_Crop,ori_img, license_baru = searching(ori_img, loop)

        # only save 5 same license each time (verification)
        if license_baru == "":
            print("no characters were detected\n")
        else:
            if len(licenses_verify) == N_VERIFY and len(set(licenses_verify)) == 1:
                if old_license== license_baru:
                    print(f"still = {old_license}\n")
                else:
                    # show and save verified plate
                    print(f"A new license plate read from image = {license_baru} \n")
                    cv2.imshow(license_baru,ori_img)
                    file_name = f"Hasil/{license_baru}.png"
                    cv2.imwrite(file_name, Plate_Crop)
                    old_license= license_baru
                    licenses_verify = []
                    print(licenses_verify)
                    save_plate(license_baru,file_name)
                    cv2.waitKey(5)
                    gate.start()
            else:
                if len(licenses_verify) == N_VERIFY:
                    # drop first if reach the N_VERIFY
                    licenses_verify = licenses_verify[1:]
                licenses_verify.append(license_baru)

        # add text and rectangle, just for information and bordering
        # cv2.rectangle(ori_img,
        #               ((ori_img.shape[1] // 2 - 250), (ori_img.shape[0] // 2 - 100)),
        #               ((ori_img.shape[1] // 2 + 250), (ori_img.shape[0] // 2 + 100)), SCALAR_GREEN,
        #               3)
        cv2.imshow("img_ori", ori_img)
        cv2.waitKey(14)

        key = cv2.waitKey(5) & 0xFF

        if key == 27:  # if the 'q' key is pressed, stop the loop
            camera.release()  # cleanup the camera and close any open windows
            break
    return
# end main


def drawRedRectangleAroundPlate(img_ori, licPlate):
    p2fRectPoints = cv2.boxPoints(licPlate.rrLocationOfPlateInScene)  # Membuat Rectangle
    a1,a2=tuple(p2fRectPoints[0])
    b1,b2=tuple(p2fRectPoints[1])
    c1,c2=tuple(p2fRectPoints[2])
    d1,d2=tuple(p2fRectPoints[3])
    cv2.line(img_ori, (int(a1),int(a2)), (int(b1),int(b2)), SCALAR_RED, 2)  # draw 4 red lines
    cv2.line(img_ori, (int(b1),int(b2)), (int(c1),int(c2)), SCALAR_RED, 2)
    cv2.line(img_ori, (int(c1),int(c2)), (int(d1),int(d2)), SCALAR_RED, 2)
    cv2.line(img_ori, (int(d1),int(d2)), (int(a1),int(a2)), SCALAR_RED, 2)
# end function


def writeLicensePlateCharsOnImage(img_ori, licPlate):
    # Titik buat area penulisan text pada Citra
    ptCenterOfTextAreaX = 0
    ptCenterOfTextAreaY = 0

    # Titik bagian Kiri dari penulisan text pada Citra
    ptLowerLeftTextOriginX = 0
    ptLowerLeftTextOriginY = 0

    sceneHeight, sceneWidth, sceneNumChannels = img_ori.shape
    plateHeight, plateWidth, plateNumChannels = licPlate.imgPlate.shape

    intFontFace = cv2.FONT_HERSHEY_SIMPLEX  # Jenis font yang ditampilkan pada Citra
    fltFontScale = float(plateHeight) / 25.0
    intFontThickness = int(round(fltFontScale * 3.5))

    # Memanggil font dalam Citra dengan fungsi getTextSize pada OpenCv
    textSize, baseline = cv2.getTextSize(licPlate.strChars, intFontFace, fltFontScale, intFontThickness)

    ((intPlateCenterX, intPlateCenterY), (intPlateWidth, intPlateHeight), fltCorrectionAngleInDeg) = licPlate.rrLocationOfPlateInScene

    intPlateCenterX = int(intPlateCenterX)
    intPlateCenterY = int(intPlateCenterY)

    # Lokasi horizontal text sama dengan plat
    ptCenterOfTextAreaX = int(intPlateCenterX)

    if intPlateCenterY < (sceneHeight * 0.75):  # Posisi ketika Plat berada di 3/4 dari Citra
        ptCenterOfTextAreaY = int(round(intPlateCenterY)) + int(
            round(plateHeight * 1.6))  # Menulis karakter di bawah plat
    else:  # Posisi Plat ketika berada di 1/4 dari Citra
        ptCenterOfTextAreaY = int(round(intPlateCenterY)) - int(
            round(plateHeight * 1.6))  # Menulis Karakter di atas plat
    # end if

    # unpack text size width dan height
    textSizeWidth, textSizeHeight = textSize

    ptLowerLeftTextOriginX = int(ptCenterOfTextAreaX - (textSizeWidth / 2))
    ptLowerLeftTextOriginY = int(ptCenterOfTextAreaY + (textSizeHeight / 2))

    # Menulis Karakter text yang dikenali kedalam Citra
    cv2.putText(img_ori, licPlate.strChars, (ptLowerLeftTextOriginX, ptLowerLeftTextOriginY), intFontFace,
                fltFontScale, SCALAR_RED, intFontThickness)


def searching(img_ori, loop):
    licenses = ""
    if img_ori is None:  # if image was not read successfully
        print("error: image not read from file \n")  # print error message to std out
        os.system("pause")  # pause so user can see error message
        return
        # end if

    # detect plates
    listOfPossiblePlates = Deteksi_Plat.detectPlatesInScene(img_ori)
    # detect chars in plates
    
    listOfPossiblePlates = Deteksi_Karakter.detectCharsInPlates(listOfPossiblePlates)
    
    plateCrop=""
    if not loop:
        cv2.imshow("img_ori", img_ori)

    if len(listOfPossiblePlates) == 0:
        if not loop:  # if no plates were found
            print("no license plates were detected\n")  # inform user no plates were found
    else:  # else
        # if we get in here list of possible plates hgias at leat one plate
        # sort the list of possible plates in DESCENDING order (most number of chars to least number of chars)
        listOfPossiblePlates.sort(key=lambda possiblePlate: len(possiblePlate.strChars), reverse=True)
        # suppose the plate with the most recognized chars (the first plate in sorted by string length descending
        # order) is the actual plate
        licPlate = listOfPossiblePlates[0]
          # show crop of plate and threshold of plate
        cv2.imshow("imgThresh", licPlate.imgThresh)
        plateCrop=licPlate.imgPlate
        cv2.imshow("plat crop",plateCrop)
            
        if len(licPlate.strChars) == 0:  # if no chars were found in the plate
            if not loop:
                print("no characters were detected\n")
                return  # show message
            # end if
        drawRedRectangleAroundPlate(img_ori, licPlate)
        writeLicensePlateCharsOnImage(img_ori, licPlate)
        licenses = licPlate.strChars



    return plateCrop,img_ori, licenses
# end function

def save_plate(num,img):
    global db
    file = 'information.csv'
    data=num+";"+img
    with open(file, 'a',newline="") as f:
        csv_writer = writer(f)
        csv_writer.writerow([data])
def load_data():
    global db
    file = open('information.csv')
    csvreader = csv.reader(file)
    
    header = next(csvreader)
    for row in csvreader:
        db.append(row)
    
    file.close()
    
if __name__ == "__main__":
    load_data()
    main()
