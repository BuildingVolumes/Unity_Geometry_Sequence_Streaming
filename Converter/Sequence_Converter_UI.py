import os
import sys
import configparser
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askdirectory
import dearpygui.dearpygui as dpg
import Sequence_Converter

class ConverterUI:

    #UI IDs for the DearPyGUI
    text_input_Dir_ID = 0
    text_output_Dir_ID = 0
    text_error_log_ID = 0
    text_info_log_ID = 0
    progress_bar_ID = 0

    ### +++++++++++++++++++++++++  PACKAGE INTO SINGLE EXECUTABLE ++++++++++++++++++++++++++++++++++
    #Use this prompt in the terminal to package this script into a single executable for your system
    #You need to have PyInstaller installed in your local environment
    # pyinstaller SequenceConverter_UI.py --collect-all=pymeshlab --icon=resources/logo.ico -F 

    # determine if application is a script file or frozen exe and get the executable path
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)

    application_path += "\\"

    path_to_resources = "resources\\"
    path_to_config = application_path + path_to_resources + "config.ini"
    config = None
    isRunning = False
    processed_files = 0

    no_path_warning = "[No folder set]"
    path_to_input_sequence = no_path_warning
    path_to_output_sequence = no_path_warning
    path_to_output_sequence_proposed = ""
    last_image_path = ""
    last_model_path = ""
    input_sequence_list_models = []
    input_sequence_list_images = []
    generate_DDS = True
    generate_ATSC = True

    valid_model_types = ["obj", "3ds", "fbx", "glb", "gltf", "obj", "ply", "ptx", "stl", "xyz", "pts"]
    valid_image_types = ["jpg", "jpeg", "png", "tiff", "dds", "bmp", "tga"]

    converter = Sequence_Converter.SequenceConverter()

    # --- UI Callbacks ---

    def open_input_dir_cb(self):
        selectedDir = self.open_file_dialog(self.path_to_input_sequence)
        self.set_input_files(selectedDir)

    def open_output_dir_cb(self):
        if(self.path_to_output_sequence is None or len(self.path_to_output_sequence) < 1):
            selectedDir = self.open_file_dialog(self.path_to_input_sequence)
        else:
            selectedDir = self.open_file_dialog(self.path_to_output_sequence)
        
        self.set_output_files(selectedDir)

    def cancel_processing_cb(self):
        self.termination_signal.set()

    def set_DDS_enabled_cb(self, sender, app_data):
        self.generate_DDS = app_data

    def set_ATSC_enabled_cb(self, sender, app_data):
        self.generate_ATSC = app_data

    def start_conversion_cb(self):

        if(self.isRunning):
            return
        
        self.isRunning = True
        self.termination_signal.clear()

        self.info_text_clear()
        self.error_text_clear()

        if(self.input_valid == False):
            self.error_text_set("Input files are not configured correctly")
            return False

        if(self.output_valid == False and self.path_to_output_sequence_proposed == "" ):
            self.error_text_set("Output folder is not configured correctly")
            return False
        
        if(len(self.input_sequence_list_images) > 1 and len(self.input_sequence_list_models) != len(self.input_sequence_list_images)):
            self.error_text_set("You need to either supply one texture per frame, or one texture for the whole sequence")
            return False

        if(self.output_valid == False and len(self.path_to_output_sequence) > 1 ):
            if not (os.path.exists(self.path_to_output_sequence_proposed)):
                os.mkdir(self.path_to_output_sequence_proposed)

        self.processed_files = 0
        self.converter.start_conversion()

        self.info_text_set("Converting...")
        self.set_progressbar(0)

    # --- File Handeling ---

    def open_file_dialog(path):
        Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
        
        if(path is None):
            new_input_path = askdirectory() 
        else:
            new_input_path = askdirectory(initialdir=path, )

        return new_input_path

    def set_input_files(self, new_input_path):

        self.input_valid = False

        self.error_text_clear()

        self.input_sequence_list_images.clear()
        self.input_sequence_list_models.clear()

        res = self.validate_input_files(new_input_path)

        if(res == True):
            path_to_input_sequence = new_input_path
            self.input_path_label_set(path_to_input_sequence)
            self.error_text_set("Input files set!")

            # Propose an output dir
            self.set_proposed_output_files(path_to_input_sequence)

            self.input_valid = True
            self.save_config("input", path_to_input_sequence)
            
        else:
            self.info_text_clear()
            self.error_text_set(res)

    def validate_input_files(self, input_path):

            if(os.path.exists(input_path) == False):
                return "Folder does not exist!"

            files = os.listdir(input_path)
            
            #Sort the files into model and images
            for file in files:
                splitted_path = file.split(".")
                file_ending = splitted_path[len(splitted_path) - 1]

                if(file_ending in self.valid_model_types):
                    self.input_sequence_list_models.append(file)
                
                elif(file_ending in self.valid_image_types):
                    self.input_sequence_list_images.append(file)

            if(len(self.input_sequence_list_models) < 1 and len(self.input_sequence_list_images) < 1):
                return "No model/image files found in folder!"

            self.input_sequence_list_models.sort()
            self.input_sequence_list_images.sort()

            return True

    def set_proposed_output_files(self, input_path):

        if(len(self.path_to_output_sequence) < 1 or self.path_to_output_sequence == self.no_path_warning):
            self.path_to_output_sequence_proposed = input_path + "\\converted"
            self.output_path_label_set("Proposed path: " + self.path_to_output_sequence_proposed)

    def set_output_files(self, new_output_path):

        self.output_valid = False

        self.info_text_clear()
        self.error_text_clear()

        if(os.path.exists(new_output_path) == True):
            self.path_to_output_sequence = new_output_path
            self.output_path_label_set(self.path_to_output_sequence)
            self.info_text_set("Output folder set!")
            self.output_valid = True
            self.path_to_output_sequence_proposed = ""

        else:
            self.info_text_clear()
            self.error_text_set("Error: Output directory is not valid!")

    def get_output_path(self):
        if(len(self.path_to_output_sequence) > 1 and self.path_to_output_sequence_proposed == ""):
            return self.path_to_output_sequence
        else:
            return self.path_to_output_sequence_proposed

    def load_config(self):

        #Create config on first starup
        if not (os.path.exists(self.path_to_config)):
            config['Paths'] = {}
            config['Paths']['input'] = ""
            with open(self.path_to_config, "w") as configfile:
                config.write(configfile)
            print("Written config first time")
        
        config.read(self.path_to_config)

    def read_config(key):
        global config
        return config['Paths'][key]

    def save_config(self, key, value):
        global config 
        config['Paths'][key] = value
        with open(self.path_to_config, "w") as configfile:
                config.write(configfile)


    # --- Main UI ---

    def advance_progressbar(self, error):

        self.progressbarLock.acquire()

        self.processed_files += 1

        if(self.termination_signal.is_set() == False):
            self.set_progressbar(self.processed_files / self.total_file_count)
            self.info_text_set("Converting: " + str(self.processed_files) + " / " + str(self.total_file_count))

        else:
            self.set_progressbar(1)
            self.info_text_set("Canceling...")

        if(self.processed_files == self.total_file_count):
            self.finish_conversion()

        self.progressbarLock.release()

    def finish_conversion(self):     

        if(self.termination_signal.is_set()):
            self.info_text_set("Canceled!")
        else:
            self.metaData.write_metaData(self.path_to_output_sequence)
            self.info_text_set("Finished!")
        
        self.set_progressbar(0)
        self.isRunning = False
        self.converter.finish_process()

    def set_progressbar(self, progress):
        dpg.set_value(self.progress_bar_ID, progress)

    def info_text_set(self, info_text):
        dpg.set_value(self.text_info_log_ID, info_text)

    def info_text_clear(self):
        dpg.set_value(self.text_info_log_ID, "")

    def error_text_set(self, error_text):
        dpg.set_value(self.text_error_log_ID, error_text)

    def error_text_clear(self):
        dpg.set_value(self.text_error_log_ID, "")

    def input_path_label_set(self, input_path):
        dpg.set_value(self.text_input_Dir_ID, input_path)

    def output_path_label_set(self, output_path):
        dpg.set_value(self.text_output_Dir_ID, output_path)


    def RunUI(self):

        dpg.create_context()
        dpg.configure_app(manual_callback_management=True)
        dpg.create_viewport(height=400, width=500, title="Geometry Sequence Converter")
        dpg.setup_dearpygui()

        with dpg.window(label="Geometry Sequence Converter", tag="main_window", min_size= [400, 500]):

            dpg.add_button(label="Select Input Directory", callback=lambda:self.open_input_dir_cb())
            self.text_input_Dir_ID = dpg.add_text(self.path_to_input_sequence, wrap=450)
            dpg.add_spacer(height=40)

            dpg.add_button(label="Select Output Directory", callback=lambda:self.open_output_dir_cb())
            self.text_output_Dir_ID = dpg.add_text(self.path_to_output_sequence, wrap=450)

            dpg.add_spacer(height=30)

            dpg.add_checkbox(label="Convert textures for desktop devices(DDS)", default_value=True, callback=self.set_DDS_enabled_cb)
            dpg.add_checkbox(label="Generate textures mobile devices (ATSC)", default_value=True, callback=self.set_ATSC_enabled_cb)

            dpg.add_spacer(height=30)

            self.text_error_log_ID = dpg.add_text("", color=[255, 0, 0], wrap=500)
            dpg.add_same_line()
            self.text_info_log_ID = dpg.add_text("", color=[255, 255, 255], wrap=500)

            self.progress_bar_ID = dpg.add_progress_bar(default_value=0, width=470)
            dpg.add_spacer(height=5)
            dpg.add_button(label="Start Conversion", callback=lambda:self.start_conversion_cb())
            dpg.add_same_line()
            dpg.add_button(label="Cancel", callback=lambda:self.cancel_processing_cb())
            dpg.add_same_line()
            dpg.add_input_int(label="Thread count", default_value=8, min_value=0, max_value=256, width=100, tag="threadCount")


        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.config = configparser.ConfigParser()
        self.load_config()
        self.set_input_files(self.read_config("input"))

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            jobs = dpg.get_callback_queue()
            dpg.run_callbacks(jobs)

        # Shutdown threads when they are still running
        self.cancel_processing_cb()

        dpg.destroy_context()

if (__name__ == '__main__'):
    UI = ConverterUI()
    UI.RunUI()