import os
import subprocess
import pymeshlab as ml
import numpy as np
from multiprocessing.pool import ThreadPool
from threading import Lock
from threading import Event
import Sequence_Metadata
import Sequence_Converter_UI

class SequenceConverter:

    is_pointcloud = False
    input_valid = False
    output_valid = False
    terminate_processing = False

    UI = Sequence_Converter_UI.ConverterUI()
    metaData = Sequence_Metadata.MetaData()
    progressbarLock = Lock()
    termination_signal = Event()

    modelPaths = []
    imagePaths = []
    modelPool = None
    texturePool = None

    total_file_count = 0
    max_active_threads = 8

    def start_conversion(self, model_paths_list, image_paths_list, threadCount):       

        self.metaData = Sequence_Metadata.MetaData()
        self.terminate_conversion = False
        self.modelPaths = model_paths_list
        self.imagePaths = image_paths_list

        modelCount = len(model_paths_list)
        textureCount = len(image_paths_list)
        self.total_file_count =  modelCount + textureCount

        self.metaData.headerSizes = [None] * modelCount
        self.metaData.verticeCounts = [None] * modelCount
        self.metaData.indiceCounts = [None] * modelCount

        self.max_active_threads= threadCount
    
        self.process_images()
        self.process_models()

    def terminate_conversion(self):
        self.terminate_conversion = True

    def finish_process(self):

        waitOnClose = True
        while(waitOnClose):
            try:
                waitOnClose = False
                self.modelPool.close()
            except:
                waitOnClose = True
        
        waitOnClose = True
        while(waitOnClose):
            try:
                waitOnClose = False
                self.texturePool.close()
            except:
                waitOnClose = True
        
        if(self.modelPool is not None):
            self.modelPool.close()
            self.modelPool.join()

        if(self.texturePool is not None):
            self.texturePool.close()
            self.texturePool.join()

    def process_models(self, inputPath, outputPath, processFinishedCB):

        if(len(self.modelPaths) < self.max_active_threads):
            threads = len(self.modelPaths)
        else:
            threads = self.max_active_threads

        modelPool = ThreadPool(processes= threads)
        modelPool.map_async(self.convert_model, self.modelPaths)

    def convert_model(self, file, input_path, output_path, process_finished_cb):

        listIndex = self.modelPaths.index(file)

        if(self.terminate_processing):
            process_finished_cb(False)
            return

        splitted_file = file.split(".")
        splitted_file.pop() # We remove the last element, which is the file ending
        file_name = ''.join(splitted_file)

        inputfile = input_path + "\\"+ file
        outputfile =  output_path + "\\" + file_name + ".ply"

        ms = ml.MeshSet()

        try:
            ms.load_new_mesh(inputfile)
        except:
            process_finished_cb(True, "Error opening file: " + inputfile)
            return    

        if(self.terminate_processing):
            process_finished_cb(False)
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

        
        if(self.terminate_processing):
            process_finished_cb(False)
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

        if(self.terminate_processing):
            process_finished_cb(False)
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

        self.metaData.set_metadata_Model(vertexCount, indiceCount, headerSize, bounds, geoType, has_UVs, listIndex)

        process_finished_cb(True)    

    def process_images(self, file, input_path, output_path, process_finished_cb):
        texturePool = ThreadPool(processes= self.max_active_threads)
        texturePool.map_async(self.convert_image, self.input_sequence_list_images)

    def convert_image(self, file, input_path, resource_path, output_path, process_finished_cb):

        if(self.terminate_processing):
            process_finished_cb(False)
            return

        splitted_file = file.split(".")
        splitted_file.pop() # We remove the last element, which is the file ending
        file_name = ''.join(splitted_file)

        inputfile = input_path + "\\"+ file
        outputfile =  output_path + "\\" + file_name + ".dds"

        cmd = resource_path + "texconv -m 1 -f DXT1 -y -srgb " + inputfile + " -o " + output_path
        texconv = subprocess.run(cmd)

        if(texconv.returncode != 0):
            process_finished_cb(True, "Error converting texture: " + inputfile)

        height = -1
        width = -1

        # We don't need to do this for every file, just the first one
        if(self.metaData.textureHeight == 0 or self.metaData.textureWidth == 0):
            with open(outputfile, mode='rb') as file: # b is important -> binary
                fileContent = file.read()
                height = fileContent[13] * 256 + fileContent[12]
                width = fileContent[17] * 256 + fileContent[16]

        size = os.path.getsize(outputfile) - 128

        if(len(self.imagePaths) == 1):
            textureMode = Sequence_Metadata.TextureMode.single
        if(len(self.imagePaths) > 1):
            textureMode = Sequence_Metadata.TextureMode.perFrame

        self.metaData.set_metadata_texture(width, height, size, textureMode)

        process_finished_cb()




