from PIL import Image
import numpy
from picamera2 import Picamera2, Preview
import time

# camera
picam2 = Picamera2()
#camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
#camera_config = picam2.create_still_configuration(main={"size": (800, 50)}, lores={"size": (400, 25)}, display="lores")
#picam2.configure(camera_config)

# function to find derivative of array
def find_inf_pt(arr):
    # calc differences
    diffs = numpy.diff(arr)
    # find index
    inflection_id = numpy.argmax(diffs) + 1
    return inflection_id

# capture hopper image
def cam_cap(name):
    #camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
    camera_config = picam2.create_still_configuration(main={"size": (800, 50)}, lores={"size": (400, 25)}, display="lores")
    picam2.configure(camera_config)
    time.sleep(1)
    picam2.start_preview(Preview.QTGL)
    picam2.start()
    time.sleep(2)
    picam2.capture_file(name)
    picam2.stop()

def cam_full_cap(name):
    camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
    picam2.configure(camera_config)
    time.sleep(1)
    #picam2.start_preview(Preview.QTGL)
    picam2.start()
    time.sleep(2)
    picam2.capture_file("test.jpg")
    picam2.stop_preview()
    picam2.stop()
    
# process image for measurement
def img_process(name): # nominally 'test.jpg'
    #load image and convert
    img = Image.open(name)
    # array
    np_img = numpy.array(img)
    # average strip in the center
    np_av_img = numpy.mean(np_img, axis=0, keepdims=True)
    # convert the third axis array into a brightness value
    bright_array = (
        0.2126 * np_av_img[:, :, 0] +
        0.7152 * np_av_img[:, :, 1] +
        0.0722 * np_av_img[:, :, 2]
    )
    # round the array values from floats to integers, input bright_array
    rnd_array = [numpy.round(x) for x in bright_array]
    # convert the array which is all the values in index zero to a normal array
    simple_array = rnd_array[0]
    # optional reverse array, to swap the values around if they are HIGH to LOW, rather than LOW to HIGH
    sim_rev_array = simple_array[::-1]
    # return the output
    return sim_rev_array
    
cam_cap('food_level_meas.jpg') # grab image
data_out = img_process('food_level_meas.jpg') # process image
print(find_inf_pt(data_out))

time.sleep(4)

cam_full_cap('full_frame_image.jpg')
    