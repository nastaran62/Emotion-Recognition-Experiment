import os
import time
import random
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib
import multiprocessing
from screeninfo import get_monitors
from questionnaire import Questionnaire
from video import VideoStreaming
from eeg import EEGStreaming
import argparse


monitors = get_monitors()
image_width =monitors[1].width
image_height =monitors[1].height
STIMULI_PATH = "stimuli/"
Fixation_CROSS_IMAGE_PATH = "fixation_cross.jpg"
DONE_IMAGE_PATH = "done.jpg"
STIMULI_SHOW_TIME = 5
FIXATION_CROSS_SHOW_TIME = 1
GRAY_IMAGE_SHOW_TIME = 2

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--subject_number", help="The subject number")
args = parser.parse_args()
subject_number = args.subject_number

class ImageWindow(Gtk.Window):
    def __init__(self, image_path, timeout):
        Gtk.Window.__init__(self, title="")

        self._timeout = timeout
        image_box = Gtk.Box()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, image_width,image_height, False)
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image_box.pack_start(image, False, False, 0)
        self.add(image_box)

        self.modal = True
        self.fullscreen()

        image_box.show()
        image.show()

    def show_window(self):
        GLib.timeout_add_seconds(self._timeout, self.destroy)
        self.show()

class BackgroudWindow(Gtk.Window):
    def __init__(self, image_path, start_delay):
        Gtk.Window.__init__(self, title="")
        self._start_delay = start_delay

        image_box = Gtk.Box()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, image_width,image_height, False)
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image_box.pack_start(image, False, False, 0)
        self.add(image_box)

        self._image_index = 0
        self._stimuli_list = os.listdir(STIMULI_PATH)
        random.shuffle(self._stimuli_list)

        # Initializing recorders
        self._video_queue = multiprocessing.Queue()
        self._eeg_queue = multiprocessing.Queue()
        video_streaming = VideoStreaming(self._video_queue)
        eeg_streaming = EEGStreaming(self._eeg_queue)
        eeg_streaming.start()
        video_streaming.start()
        time.sleep(5)

    def show(self):
        '''
        Shows the backgroun window (A gray image)
        '''
        self.connect("destroy", Gtk.main_quit)
        self.fullscreen()
        self.show_all()

        GLib.timeout_add_seconds(self._start_delay, self._show_next)

        Gtk.main()

    def _show_next(self, *args):
        '''
        Shows the next stimuli
        '''

        if self._image_index >= len(self._stimuli_list):
            # Done
            self._video_queue.put("terminate")
            self._eeg_queue.put("terminate")
            self.destroy()
            return
        stimuli = ImageWindow(STIMULI_PATH + self._stimuli_list[self._image_index], STIMULI_SHOW_TIME)

        # Start video and eeg record
        self._video_queue.put("p-{}-s{}-t{}".format(subject_number, self._image_index, str(time.time())))
        self._eeg_queue.put("p-{}-s{}-t{}".format(subject_number, self._image_index, str(time.time())))

        # This will call the questionnaire showing after disapearing the stimili
        stimuli.connect("destroy", self._show_questionnaire)

        stimuli.show_window()

    def _show_questionnaire(self, *args):
        '''
        showing questionnaire
        '''
        # Stop video and eeg record
        self._video_queue.put("stop_record")
        self._eeg_queue.put("stop_record")

        questionnaire = Questionnaire(subject_number, self._image_index)

        # This will call the fixation cross showing after disapearing the questionnaire
        questionnaire.connect("destroy", self._show_fixation_cross)
        questionnaire.show()
        time.sleep(GRAY_IMAGE_SHOW_TIME)

    def _show_fixation_cross(self, *args):
        '''
        Showing fixation cross
        '''
        self._image_index = self._image_index + 1
        if self._image_index >= len(self._stimuli_list):
            fixation_cross = \
                ImageWindow(DONE_IMAGE_PATH,
                            GRAY_IMAGE_SHOW_TIME + FIXATION_CROSS_SHOW_TIME)
        else:

            fixation_cross = \
                ImageWindow(Fixation_CROSS_IMAGE_PATH,
                            GRAY_IMAGE_SHOW_TIME + FIXATION_CROSS_SHOW_TIME)

        # This will call the next stimuli showing after disapearing the fixation cross
        fixation_cross.connect("destroy", self._show_next)
        fixation_cross.show_window()

def main():
    main_window = BackgroudWindow("gray_image.jpg", GRAY_IMAGE_SHOW_TIME)
    main_window.show()

main()
