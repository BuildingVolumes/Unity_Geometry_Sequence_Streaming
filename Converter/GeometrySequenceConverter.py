import os
import sys
import subprocess
import pymeshlab as ml
import dearpygui.dearpygui as dpg
import numpy as np
import configparser
from multiprocessing.pool import ThreadPool
from threading import Lock
from threading import Event
import json

### +++++++++++++++++++++++++  PACKAGE INTO SINGLE EXECUTABLE ++++++++++++++++++++++++++++++++++
#Use this prompt in the terminal to package this script into a single executable for your system
#You need to have PyInstaller installed in your local environment
# pyinstaller GeometrySequenceConverter.py --collect-all=pymeshlab --icon=resources/logo.ico -F 


# determine if application is a script file or frozen exe and get the executable path
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

application_path += "\\"

path_to_resources = "resources\\"
path_to_config = application_path + path_to_resources + "config.ini"
config = None

path_to_input_sequence = "[No folder set]"
path_to_output_sequence = "[No folder set]"
last_image_path = ""
last_model_path = ""

input_sequence_list_models = []
input_sequence_list_images = []

is_running = False
is_pointcloud = False
input_valid = False
output_valid = False

metaDataLock = Lock()
progressbarLock = Lock()
termination_signal = Event()
modelPool = None
texturePool = None

processed_files = 0
total_file_count = 0
max_active_threads = 4

valid_model_types = ["obj", "3ds", "fbx", "glb", "gltf", "obj", "ply", "ptx", "stl", "xyz", "pts"]
valid_image_types = ["jpg", "jpeg", "png", "tiff", "dds", "bmp", "tga"]

metaData = {
    "geometryType" : None,
    "textureMode" : None,
    "maxVertexCount": 0,
    "maxTriangleCount" : 0,
    "maxBounds" : [0, 0, 0, 0, 0, 0],
    "textureWidth" : 0,
    "textureHeight" : 0,
    "models" : [],
    "textures" : []
}


def setup_converter():

    global processed_files
    global total_file_count
    global max_active_threads
    global termination_signal
    global is_running

    if(is_running):
        return

    termination_signal.clear()

    dpg.set_value(text_error_log_ID, "")
    dpg.set_value(text_info_log_ID, "")

    if(input_valid == False):
        dpg.set_value(text_error_log_ID, "Input files are not configured correctly")
        return False

    if(output_valid == False):
        dpg.set_value(text_error_log_ID, "Output folder is not configured correctly")
        return False

    max_active_threads= dpg.get_value("threadCount")
    total_file_count = len(input_sequence_list_images) + len(input_sequence_list_models)
    
    processed_files = 0
    dpg.set_value(progress_bar_ID, 1 / total_file_count)

    process()

def process():

    global is_running
    is_running = True
    process_models()
    process_images()

    dpg.set_value(text_info_log_ID, "Converting...")
    dpg.set_value(progress_bar_ID, 0)

def advance_progressbar():

    global progressbarLock
    global total_file_count
    global processed_files

    progressbarLock.acquire()

    processed_files += 1

    if(termination_signal.is_set() == False):
        dpg.set_value(progress_bar_ID, processed_files / total_file_count)
        progresstext = "Converting: " + str(processed_files) + " / " + str(total_file_count)
        dpg.set_value(text_info_log_ID, progresstext)

    else:
        dpg.set_value(progress_bar_ID, 1)
        dpg.set_value(text_info_log_ID, "Canceling...")

    progressbarLock.release()

    if(processed_files == total_file_count):
        finish_process()

def finish_process():

    global is_running
    global termination_signal
    global modelPool
    global texturePool

    write_metaData(path_to_output_sequence)
    dpg.set_value(text_info_log_ID, "Finished!")

    if(termination_signal.is_set()):
        dpg.set_value(text_info_log_ID, "Canceled!")
    
    dpg.set_value(progress_bar_ID, 0)

    modelPool.close()
    texturePool.close()
    is_running = False

def process_models():

    global modelPool
    modelPool = ThreadPool(processes= max_active_threads)
    modelPool.map_async(convert_model, input_sequence_list_models)

def convert_model(file):

    global is_pointcloud
    global termination_signal

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    splitted_file = file.split(".")
    splitted_file.pop() # We remove the last element, which is the file ending
    file_name = ''.join(splitted_file)

    inputfile = path_to_input_sequence + "\\"+ file
    outputfile =  path_to_output_sequence + "\\" + file_name + ".ply"

    ms = ml.MeshSet()

    ms.load_new_mesh(inputfile)

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    faceCount = len(ms.current_mesh().face_matrix())        
    
    is_pointcloud = True
    has_UVs = False

    #Is the file a mesh or pointcloud?        
    if(faceCount > 0):
        is_pointcloud = False

    if(ms.current_mesh().has_wedge_tex_coord() == True or ms.current_mesh().has_vertex_tex_coord() == True):
        has_UVs = True

    #There is a chance that the file might have wedge tex
    #coordinates which are unsupported in Unity, so we convert them
    #Also we need to ensure that our mesh contains only triangles!
    if(is_pointcloud == False):
        
        if(ms.current_mesh().has_wedge_tex_coord() == True):
            ms.apply_filter("compute_texcoord_transfer_wedge_to_vertex")
        
        ms.apply_filter("meshing_poly_to_tri")

    
    if(termination_signal.is_set()):
        advance_progressbar()
        return

    vertices = None
    vertice_colors = None
    faces = None
    uvs = None

    #Load type specific attributes
    if(is_pointcloud == True):
        vertices = ms.current_mesh().vertex_matrix().astype(np.float32)
        vertice_colors = ms.current_mesh().vertex_color_array()
    
    else:
        vertices = ms.current_mesh().vertex_matrix().astype(np.float32)
        faces = ms.current_mesh().face_matrix()

        if(has_UVs == True):     
            uvs = ms.current_mesh().vertex_tex_coord_matrix().astype(np.float32)

    vertexCount = len(vertices)

    if(faces is not None):
        triangleCount = len(faces)
    else:
        triangleCount = 0

    bounds = ms.current_mesh().bounding_box()

    if(is_pointcloud == True):
        geoType = "points"
    else:
        geoType = "mesh"

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    set_metadata_Model(vertexCount, triangleCount, bounds, geoType)
    
    #The meshlab exporter doesn't support all the features we need, so we export the files manually
    #to PLY with our very stringent structure. This is needed because we want to keep the
    #work on the Unity side as low as possible, so we basically want to load the data from disk into the memory
    #without needing to change anything

    with open(outputfile, 'wb') as f:

        #constructing the ascii header
        header = "ply" + "\n"
        header += "format binary_little_endian 1.0" + "\n"
        header += "comment Exported for use in Unity Geometry Streaming Plugin" + "\n"

        header += "element vertex " + str(len(vertices)) + "\n"
        header += "property float x" + "\n" 
        header += "property float y" + "\n"
        header += "property float z" + "\n"

        if(is_pointcloud == True):
            header += "property uchar red" + "\n"
            header += "property uchar green" + "\n"
            header += "property uchar blue" + "\n"
            header += "property uchar alpha" + "\n"
        
        else:
            if(has_UVs == True):
                header += "property float s" + "\n" 
                header += "property float t" + "\n"
            header += "element face " + str(len(faces)) + "\n"
            header += "property list uchar uint vertex_indices" + "\n"

        header += "end_header\n"

        f.write(header.encode('ascii'))


        #Constructing the mesh data, as binary
        body = []

        if(is_pointcloud == True):
            
            verticeRaw = vertices.tobytes()
            vertice_colors_raw = vertice_colors.tobytes()

            for index, line in enumerate(vertices):
                #Copy 3 floats for xyz coordinates
                body.extend(verticeRaw[index * 3 * 4:(index * 3 * 4) + 12])

                #Copy 4 bytes for Color and convert from BGRA to RGBA
                body.append(vertice_colors_raw[(index * 4) + 2])
                body.append(vertice_colors_raw[(index * 4) + 1])
                body.append(vertice_colors_raw[(index * 4) + 0])
                body.append(vertice_colors_raw[(index * 4) + 3])


        else:
            verticeRaw = vertices.tobytes()
            faceRaw = faces.tobytes()

            if(has_UVs == True):
                uvRaw = uvs.tobytes()

            for index, line in enumerate(vertices):
                #Copy 3 floats for xyz coordinates
                body.extend(verticeRaw[index * 3 * 4:(index * 3 * 4) + 12])

                #Copy 2 floats of Uv texture coordinates
                if(has_UVs == True):
                    body.extend(uvRaw[index * 2 * 4:(index * 2 * 4) + 8])

            for index, line in enumerate(faces):
                
                #For PLY files, each indice bundle has to mention how much indices it contains
                #As we only have triangular faces, it will always be three
                indiceCount = [3]
                body.extend(bytes(indiceCount))

                #Copy three UInt32s as face indices
                body.extend(faceRaw[index * 3 * 4: (index * 3 * 4) + 12])


        f.write(bytes(body))

    advance_progressbar()    

def process_images():

    global texturePool
    texturePool = ThreadPool(processes= max_active_threads)
    texturePool.map_async(convert_image, input_sequence_list_images)

def convert_image(file):

    global last_image_path
    global termination_signal

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    splitted_file = file.split(".")
    splitted_file.pop() # We remove the last element, which is the file ending
    file_name = ''.join(splitted_file)

    inputfile = path_to_input_sequence + "\\"+ file
    outputfile =  path_to_output_sequence + "\\" + file_name + ".dds"

    cmd = [application_path + path_to_resources + "nvcompress", "-nomips", "-bc1", "-silent", inputfile, outputfile]
    subprocess.call(cmd)

    height = -1
    width = -1

    # We don't need to do this for every file, just the first one
    if(metaData["height"] == 0 or metaData["width"] == 0):
        with open(outputfile, mode='rb') as file: # b is important -> binary
            fileContent = file.read()
            height = fileContent[13] * 256 + fileContent[12]
            width = fileContent[17] * 256 + fileContent[16]

    size = os.path.getsize(outputfile) - 128

    set_metadata_texture(width, height, size)


def set_metadata_Model(vertexCount, triangleCount, bounds, geometryType):
    
    global metaDataLock
    global metaData

    metaDataLock.acquire()

    if(metaData["geometryType"] is None):
        metaData["geometryType"] = geometryType

    if(vertexCount > metaData["maxVertexCount"]):
        metaData["maxVertexCount"] = vertexCount

    if(triangleCount > metaData["maxTriangleCount"]):
        metaData["maxTriangleCount"] = triangleCount

    for maxBound in range(3):
        if metaData["maxBounds"][maxBound] < bounds.max()[maxBound]:
            metaData["maxBounds"][maxBound] = bounds.max()[maxBound]

    for minBound in range(3):
        if metaData["maxBounds"][minBound + 3] > bounds.min()[minBound]:
            metaData["maxBounds"][minBound + 3] = bounds.min()[minBound]

    metaData["models"].append((vertexCount, triangleCount))

    metaDataLock.release()

def set_metadata_texture(height, width, size):

    global metaDataLock
    global metaData

    metaDataLock.acquire()

    if(height > metaData["height"]):
        metaData["height"] = height
    
    if(width > metaData["width"]):
        metaData["width"] = width
    
    metaData["textures"].append(size)

    metaDataLock.release()



def write_metaData(outputPath):
    global metaData
    outputPath = outputPath + "/sequence.json"

    with open(outputPath, 'w') as f:
        json.dump(metaData, f)

def validate_input_files(input_path):

        if(os.path.exists(input_path) == False):
            return "Folder does not exist!"

        files = os.listdir(input_path)
        
        #Sort the files into model and images
        for file in files:
            splitted_path = file.split(".")
            file_ending = splitted_path[len(splitted_path) - 1]

            if(file_ending in valid_model_types):
                input_sequence_list_models.append(file)
            
            elif(file_ending in valid_image_types):
                input_sequence_list_images.append(file)

        if(len(input_sequence_list_models) < 1 and len(input_sequence_list_images) < 1):
            return "No model/image files found in folder!"

        input_sequence_list_models.sort()
        input_sequence_list_images.sort()

        return True


        
#----------------------- UI Logic ---------------------------


#UI IDs for the DearPyGUI
text_input_Dir_ID = 0
text_output_Dir_ID = 0
text_error_log_ID = 0
text_info_log_ID = 0
progress_bar_ID = 0


dpg.create_context()

def input_files_confirm_callback(sender, app_data):
    set_input_files(app_data["file_path_name"])


def set_input_files(new_input_path):

    global input_valid
    global path_to_input_sequence

    input_valid = False

    dpg.set_value(text_error_log_ID, "")

    input_sequence_list_images.clear()
    input_sequence_list_models.clear()

    res = validate_input_files(new_input_path)

    if(res == True):

        if(len(path_to_output_sequence) < 1):
            #Re-Initialize the output dialog, so that it goes directly to the input dir path when opening it. 
            dpg.delete_item("file_output_dialog_id")
            dpg.add_file_dialog(directory_selector=True, show=False, callback=output_files_confirm_callback, tag="file_output_dialog_id", min_size=[500, 430], default_path=new_input_path)

        path_to_input_sequence = new_input_path
        dpg.set_value(text_input_Dir_ID, path_to_input_sequence)
        dpg.set_value(text_info_log_ID, "Input files set!")
        input_valid = True
        save_config("input", path_to_input_sequence)
        dpg.delete_item("file_input_dialog_id")
        dpg.add_file_dialog(directory_selector=True, show=False, callback=input_files_confirm_callback, tag="file_input_dialog_id", min_size=[500, 430], default_path=path_to_input_sequence)       

    else:
        path_to_input_sequence = ""
        input_valid = False
        dpg.set_value(text_info_log_ID, "")
        dpg.set_value(text_error_log_ID, res)

def output_files_confirm_callback(sender, app_data):
    set_output_files(app_data["file_path_name"])


def set_output_files(new_output_path):

    global output_valid
    global path_to_output_sequence

    output_valid = False

    dpg.set_value(text_info_log_ID, "")
    dpg.set_value(text_error_log_ID, "")


    if(os.path.exists(new_output_path) == True):
        path_to_output_sequence = new_output_path
        dpg.set_value(text_output_Dir_ID, path_to_output_sequence)
        dpg.set_value(text_info_log_ID, "Output folder set!")
        output_valid = True
        save_config("output", path_to_output_sequence)
        dpg.delete_item("file_output_dialog_id")
        dpg.add_file_dialog(directory_selector=True, show=False, callback=output_files_confirm_callback, tag="file_output_dialog_id", min_size=[500, 430], default_path=path_to_output_sequence)

    else:
        path_to_output_sequence = ""
        dpg.set_value(text_info_log_ID, "")
        dpg.set_value(text_error_log_ID, "Error: Output directory is not valid!")
        output_valid = False

def copy_input_to_output_dir():
    global path_to_input_sequence
    set_output_files(path_to_input_sequence)

def cancel_processing_callback():
    global termination_signal
    termination_signal.set()

def show_input():
    dpg.show_item("file_input_dialog_id")
    try:
        dpg.set_item_pos(item="file_input_dialog_id", pos=[0,0])
    except:
        x = "DearPyGui error, nothing to worry about"

def show_output():
    dpg.show_item("file_output_dialog_id")
    try:
        dpg.set_item_pos(item="file_output_dialog_id", pos=[0,0])
    except:
        x = "DearPyGui error, nothing to worry about"

def load_config():
    global config

    #Create config on first starup
    if not (os.path.exists(path_to_config)):
        config['Paths'] = {}
        config['Paths']['input'] = ""
        config['Paths']['output'] = ""
        with open(path_to_config, "w") as configfile:
            config.write(configfile)
        print("Writte config first time")
    
    config.read(path_to_config)

def read_config(key):
    global config
    return config['Paths'][key]

def save_config(key, value):
    global config 
    config['Paths'][key] = value
    with open(path_to_config, "w") as configfile:
            config.write(configfile)


# Main UI Loop

dpg.create_viewport(height=500, width=500, title="Geometry Sequence Converter")
dpg.setup_dearpygui()


with dpg.window(label="Geometry Sequence Converter", tag="main_window", min_size= [500, 500]):
    
    dpg.add_file_dialog(directory_selector=True, show=False, callback=input_files_confirm_callback, tag="file_input_dialog_id", min_size=[500, 430], default_path=path_to_input_sequence)
    dpg.add_file_dialog(directory_selector=True, show=False, callback=output_files_confirm_callback, tag="file_output_dialog_id", min_size=[500, 430], default_path=path_to_output_sequence)

    dpg.add_button(label="Select Input Directory", callback=lambda:show_input())
    #dpg.add_text("Input sequence folder:")
    text_input_Dir_ID = dpg.add_text(path_to_input_sequence, wrap=450)
    dpg.add_spacer(height=50)

    dpg.add_button(label="Select Output Directory", callback=lambda:show_output())
    #dpg.add_text("Output sequence folder:")
    dpg.add_same_line()
    dpg.add_button(label="Set to Input Directory", callback=lambda:copy_input_to_output_dir())
    text_output_Dir_ID = dpg.add_text(path_to_output_sequence, wrap=450)

    text_error_log_ID = dpg.add_text("", color=[255, 0, 0], wrap=500, pos= [10, 370])
    dpg.add_same_line()
    text_info_log_ID = dpg.add_text("", color=[255, 255, 255], wrap=500)

    progress_bar_ID = dpg.add_progress_bar(default_value=0, width=470)
    dpg.add_spacer(height=5)
    dpg.add_button(label="Start Conversion", callback=lambda:setup_converter())
    dpg.add_same_line()
    dpg.add_button(label="Cancel", callback=lambda:cancel_processing_callback())
    dpg.add_same_line()
    dpg.add_input_int(label="Thread count", default_value=4, min_value=0, max_value=128, width=100, tag="threadCount")


dpg.show_viewport()
dpg.set_primary_window("main_window", True)

config = configparser.ConfigParser()
load_config()
set_input_files(read_config("input"))
set_output_files(read_config("output"))

while dpg.is_dearpygui_running():

    dpg.render_dearpygui_frame()

# Shutdown threads when they are still running
cancel_processing_callback()

if(modelPool is not None):
    modelPool.close()
    modelPool.join()

if(texturePool is not None):
    texturePool.close()
    texturePool.join()

dpg.destroy_context()
