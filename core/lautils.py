# Class that takes care of managing the LostArk queue.

import re
import cv2
import numpy as np
import pytesseract
from math import ceil
from .wutils import WindowsManager

class LostArkManager():

    def __init__(self, screen_res=(1920,1080)):

        self.screen_res = screen_res
        self.delta_t = 20
        self.last_avg_time = 99999
        self.last_valid_queue = 0
        self.avg_times = np.array([])
        self.avg_queue_decreases = np.array([])
        self.queue_tolerance = 100
        self.wman = WindowsManager()
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'

    def get_queue_image(self):

        # Extract queue rectangle box from the image
        # NOTE: Precision may vary on screen resolution: higher one produces
        # better images, and accurate queue inference.
        im, w, h = self.wman.get_process_screen('lost ark')

        # Convert the PIL image to opencv
        im = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)

        # Crop the rectangle box region
        rect = im[h//2:h//2+100, w//2-50:w//2+100]


        # Handle resolution:
        if self.screen_res[1] == 720:

            # CASE 720P (16:9)
            queue_img = rect[40:55, 85:115]

        elif self.screen_res[1] == 1080:

            # CASE 1080P (16:9)
            queue_img = rect[43:63, 96:147]

        else:

            # If no resolution is supported, return the whole image
            queue_img = rect

        # TODO: OTHER RESOLUTIONS

        # LESS ACCURATE
        """# Filtering out some noise with binarization and image processing
        # Thresholding the coloured image
        _, thresholded = cv2.threshold(queue_img, 90, 255, cv2.THRESH_BINARY_INV)

        # Apply erosion (since we've used the inverse binarization)
        eroded = cv2.erode(thresholded, (3,3), iterations=1)

        # Convert to grayscale
        final = cv2.cvtColor(eroded, cv2.COLOR_BGR2GRAY)"""

        # Converting to grayscale and dilating to better recognize digits
        queue_img = cv2.cvtColor(queue_img, cv2.COLOR_BGR2GRAY)
        queue_img = cv2.dilate(queue_img, (5,5), iterations=1)

        # return
        return queue_img

    def get_queue_status(self):

        # Get the process screen
        queue = self.get_queue_image()

        # Get the string queue number
        q_num = pytesseract.image_to_string(queue,
                                            lang='eng',
                                            config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789')

        # Clean the string from special characters
        clean_num = re.sub('\W+','', q_num)

        # Handle tesseract errors case: assure that there is at least one element
        # inside the avg_queue_decreases to fetch an estimate.
        if len(self.avg_queue_decreases) >= 1 and clean_num != '':
            clean_num, _, _ = self.handle_wrong_pred(clean_num, None)
            clean_num = int(clean_num)
        # Return the number
        return clean_num

    def compute_wait_time(self, cur_queue, last_queue):

        # Time needed is based off the percentage of the moving users every 20 secs,
        # since this is the refresh time of the queue server.
        # If the queue is moving, (difference not equal to 0) that means the queue
        # is moving.  Otherwise, that means we're stuck on waiting.
        # We then return the last computed avg time.

        # Handle cases in which one of the two is none
        if last_queue == '' or cur_queue== '':
            return None

        # Typecast to do operations
        cur_queue = int(cur_queue)
        last_queue = int(last_queue)

        # Handle tesseract wrong prediction: may happen that tesseract will return a
        # totally different number from the image given. This is easily solved by
        # analyzing the linear pattern involving the decreasing queue number at each
        # refresh.
        cur_queue, last_queue, delta_decrease = self.handle_wrong_pred(cur_queue, last_queue)

        # Now lets compute the time
        if cur_queue-last_queue != 0:

            # Avg time is simply calculate by the difference by the queue status
            # multiplied a minute divided by delta t (base=20). We then divide the current
            # queue by the average user per minute and obtain the avg time needed
            # in minute. delta_decrease is simply the difference between cur and last queue.
            avg_time = ceil(cur_queue/(delta_decrease*(60/self.delta_t)))

            # We reset delta_t to 20 in case has been updated in the other condition
            self.delta_t = 20

            # We assign the cur queue to the last valid queue
            self.last_valid_queue = cur_queue

            # Append the number to the avg times array
            self.avg_times = np.append(self.avg_times, avg_time)

        else:

            # If the queue is stuck, we need to increase delta_t to take track of
            # the increased amount of seconds passed without an update in the queue.
            self.delta_t += 20

            # We set avg_time to the last one computed since we cant do an estimate.
            avg_time = self.last_avg_time

            # append to the avg time array
            self.avg_times = np.append(self.avg_times, avg_time)

        # Updating the avg time with the calculated one
        self.last_avg_time = avg_time

        print('Avg time before removing outliers and windowing: {}'.format(self.avg_times))
        self.avg_times = self.remove_outliers(self.avg_times)
        print('Avg time after removing outliers and windowing: {}'.format(self.avg_times))

        return round(self.avg_times.mean())


    def handle_wrong_pred(self, cur_queue, last_queue):


        # We first check if the avg user per minute is empty, if so,
        # we append the difference of the users as first init.
        # NOTE: We must pray that tess does not recognize a wrong digit set at
        # the first iteration! this is unpredictable.
        if len(self.avg_queue_decreases) == 0:

            # Compute the users for a delta_t decrease in the queue
            # (since the refresh is every 20 sec, cur_queue - last_queue represent
            # the decrease in the queue on 20 sec basis)
            delta_decrease = last_queue - cur_queue

            # append the value to the array
            self.avg_queue_decreases = np.append(self.avg_queue_decreases, delta_decrease)

        else:

            # Check if last queue is none; this happens when the queue status calls this
            # function to get an estimate and avoid tesseract digits error. If is none,
            # Just use the last valid queue.
            if last_queue is None:
                is_check = True
                last_queue = self.last_valid_queue
                cur_queue = int(cur_queue)
            else:
                is_check = False

            # If there is at least one element, we can use the mean of the avg_queue_decreases
            # to check if it does belong to a correct prediction delimited by the interval
            # 2epsilon < delta_decrease <2epsilon. For example, if tess predicted 40000 but the
            # last queue was a 4034, that means that probably the new queue was 4000.
            # The difference then would give -35.966 instead of 34. We assure that we're in the
            # correct range.
            delta_decrease = abs(last_queue - cur_queue)

            print('Before correction: Cur {} - Last {} - Delta {} '.format(cur_queue, last_queue, delta_decrease))

            # If the delta_decrease is lesser than a certain tolerance, that means we
            # have an error
            if delta_decrease > 2*self.queue_tolerance:

                # We correct the cur_queue with an average value given by the avg decrease
                # in queue.
                cur_queue = last_queue - self.avg_queue_decreases.mean()

                # We assign the correct delta_decrease
                delta_decrease = last_queue - cur_queue

            # If we're here from the avg time function
            if not is_check:

                # Append the new value to the avg_queue_decreases
                self.avg_queue_decreases = np.append(self.avg_queue_decreases, delta_decrease)

                # Clean the array from eventual outliers
                self.avg_queue_decreases = self.remove_outliers(self.avg_queue_decreases)

        print('AVG queue decrease: {}'.format(self.avg_queue_decreases))
        print('Before correction: Cur {} - Last {} - Delta {} '.format(cur_queue, last_queue, delta_decrease))

        # Once here, we've (hopefully) corrected our values; return everything
        return cur_queue, last_queue, delta_decrease

    def remove_outliers(self, array):

        # Removing the outliers given by wrong prediction by tesseract.
        # We simply achieve that by calculating mean and std of our array,
        # and then considering values inside the gaussian bell that does not
        # go further than 4sigma from the mean.
        # NOTE: We do this only when the queue times contains more than one element.
        if len(array) != 1:

            # Get mean and std (adding an eps to zero multiplication problem)
            mean = np.mean(array) + np.finfo(np.float32).eps
            standard_deviation = np.std(array) + np.finfo(np.float32).eps

            # Compute the distances from the mean
            distance_from_mean = abs(array - mean)

            # Max deviations are 4sigma from the mean
            max_deviations = 4

            # Compute the array of boolean that are true only if the condition
            # (not being away from 2sigma) is respected
            not_outlier = distance_from_mean < max_deviations * standard_deviation

            # Apply the mask on the time array and return only the last window
            # (we do not want to calculate the mean on an huge window):
            # A window is based on the last two minutes queue.
            return array[not_outlier][-6:]

        else:

            # Else, just returnt the passed array
            return array
