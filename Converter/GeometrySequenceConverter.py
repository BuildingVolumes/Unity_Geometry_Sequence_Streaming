import os
import sys
import subprocess
import pymeshlab as ml
import numpy as np
import configparser
from multiprocessing.pool import ThreadPool
from threading import Lock
from threading import Event
import Sequence_Metadata


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

no_path_warning = "[No folder set]"
path_to_input_sequence = no_path_warning
path_to_output_sequence = no_path_warning
path_to_output_sequence_proposed = ""
last_image_path = ""
last_model_path = ""
generate_DDS = True
generate_ATSC = True

input_sequence_list_models = []
input_sequence_list_images = []

is_running = False
is_pointcloud = False
input_valid = False
output_valid = False

metaData = Sequence_Metadata.MetaData()
progressbarLock = Lock()
termination_signal = Event()
modelPool = None
texturePool = None

processed_files = 0
total_file_count = 0
max_active_threads = 8

valid_model_types = ["obj", "3ds", "fbx", "glb", "gltf", "obj", "ply", "ptx", "stl", "xyz", "pts"]
valid_image_types = ["jpg", "jpeg", "png", "tiff", "dds", "bmp", "tga"]




def setup_converter_cb():

    global is_running
    if(is_running):
        return

    global processed_files
    global total_file_count
    global max_active_threads
    global termination_signal    

    termination_signal.clear()

    dpg.set_value(text_error_log_ID, "")
    dpg.set_value(text_info_log_ID, "")

    if(input_valid == False):
        dpg.set_value(text_error_log_ID, "Input files are not configured correctly")
        return False

    if(output_valid == False and path_to_output_sequence_proposed == "" ):
        dpg.set_value(text_error_log_ID, "Output folder is not configured correctly")
        return False
    
    if(output_valid == False and len(path_to_output_sequence) > 1 ):
        if not (os.path.exists(path_to_output_sequence_proposed)):
            os.mkdir(path_to_output_sequence_proposed)

    modelCount = len(input_sequence_list_models)
    textureCount = len(input_sequence_list_images)
    total_file_count =  modelCount + textureCount


    if(textureCount > 1 and modelCount != textureCount):
        dpg.set_value(text_error_log_ID, "You need to either supply one texture per frame, or one texture for the whole sequence")
        return False

    metaData.headerSizes = [None] * modelCount
    metaData.verticeCounts = [None] * modelCount
    metaData.indiceCounts = [None] * modelCount

    max_active_threads= dpg.get_value("threadCount")
    
    processed_files = 0

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
        print("Canceling")

    if(processed_files == total_file_count):
        finish_process()

    progressbarLock.release()


def finish_process():

    global is_running
    global termination_signal
    global modelPool
    global texturePool
    global metaData

    print("Finishing")

    if(termination_signal.is_set()):
        dpg.set_value(text_info_log_ID, "Canceled!")
    else:
        metaData.write_metaData(path_to_output_sequence)
        dpg.set_value(text_info_log_ID, "Finished!")
    
    dpg.set_value(progress_bar_ID, 0)

    print("Closing threadpool")
    
    waitOnClose = True
    while(waitOnClose):
        try:
            waitOnClose = False
            modelPool.close()
        except:
            waitOnClose = True
    
    waitOnClose = True
    while(waitOnClose):
        try:
            waitOnClose = False
            texturePool.close()
        except:
            waitOnClose = True

    is_running = False
    print("Finished")

def process_models():

    global modelPool

    if(len(input_sequence_list_models) < max_active_threads):
        threads = len(input_sequence_list_models)
    else:
        threads = max_active_threads

    modelPool = ThreadPool(processes= threads)
    modelPool.map_async(convert_model, input_sequence_list_models)

def convert_model(file):

    global is_pointcloud
    global termination_signal
    global metaData

    listIndex = input_sequence_list_models.index(file)

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    splitted_file = file.split(".")
    splitted_file.pop() # We remove the last element, which is the file ending
    file_name = ''.join(splitted_file)

    inputfile = path_to_input_sequence + "\\"+ file
    outputfile =  get_output_path() + "\\" + file_name + ".ply"

    ms = ml.MeshSet()

    try:
        ms.load_new_mesh(inputfile)
    except:
        print("Could not load file: " + inputfile)
        termination_signal.set()
        dpg.set_value(text_error_log_ID, "Error opening file: " + inputfile)
        advance_progressbar()
        return    

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
        indiceCount = len(faces) * 3
    else:
        indiceCount = 0

    bounds = ms.current_mesh().bounding_box()

    if(is_pointcloud == True):
        geoType = Sequence_Metadata.GeometryType.point
    else:
        if(has_UVs == False):
            geoType = Sequence_Metadata.GeometryType.mesh
        else:
            geoType = Sequence_Metadata.GeometryType.texturedMesh

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    
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

        headerASCII = header.encode('ascii')
        headerSize = len(headerASCII)

        f.write(headerASCII)


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
                indiceArray = [3]
                body.extend(bytes(indiceArray))

                #Copy three UInt32s as face indices
                body.extend(faceRaw[index * 3 * 4: (index * 3 * 4) + 12])


        f.write(bytes(body))

    metaData.set_metadata_Model(vertexCount, indiceCount, headerSize, bounds, geoType, has_UVs, listIndex)

    advance_progressbar()    

def process_images():

    global texturePool
    texturePool = ThreadPool(processes= max_active_threads)
    texturePool.map_async(convert_image, input_sequence_list_images)

def convert_image(file):

    global termination_signal

    if(termination_signal.is_set()):
        advance_progressbar()
        return

    splitted_file = file.split(".")
    splitted_file.pop() # We remove the last element, which is the file ending
    file_name = ''.join(splitted_file)

    inputfile = path_to_input_sequence + "\\"+ file
    outputfile =  get_output_path() + "\\" + file_name + ".dds"

    cmd = application_path + path_to_resources + "texconv -m 1 -f DXT1 -y -srgb " + inputfile + " -o " + get_output_path()
    subprocess.run(cmd)

    height = -1
    width = -1

    # We don't need to do this for every file, just the first one
    if(metaData.textureHeight == 0 or metaData.textureWidth == 0):
        with open(outputfile, mode='rb') as file: # b is important -> binary
            fileContent = file.read()
            height = fileContent[13] * 256 + fileContent[12]
            width = fileContent[17] * 256 + fileContent[16]

    size = os.path.getsize(outputfile) - 128

    if(len(input_sequence_list_images) == 1):
        textureMode = Sequence_Metadata.TextureMode.single
    if(len(input_sequence_list_images) > 1):
        textureMode = Sequence_Metadata.TextureMode.perFrame

    metaData.set_metadata_texture(width, height, size, textureMode)

    advance_progressbar()


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

def get_output_path():
    if(len(path_to_output_sequence) > 1 and path_to_output_sequence_proposed == ""):
        return path_to_output_sequence
    else:
        return path_to_output_sequence_proposed
