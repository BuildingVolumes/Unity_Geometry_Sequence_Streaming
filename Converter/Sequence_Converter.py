import os
import subprocess
import pymeshlab as ml
import numpy as np
from threading import Lock
from multiprocessing.pool import ThreadPool
import Sequence_Metadata
from PIL import Image

class SequenceConverter:

    isPointcloud = False
    terminateProcessing = False

    metaData = Sequence_Metadata.MetaData()

    modelPaths = []
    imagePaths = []
    modelPool = None
    texturePool = None

    processFinishedCB = None
    inputPath = ""
    outputPath = ""
    resourcePath = ""

    convertToDDS = False
    convertToASTC = False
    convertToSRGB = False

    maxThreads = 8
    activeThreadLock = Lock()
    activeThreads = 0
    

    def start_conversion(self, model_paths_list, image_paths_list, input_path, output_path, resource_Path, processFinishedCB, threadCount, convertDDS, convertASTC, convertSRGB):       

        self.metaData = Sequence_Metadata.MetaData()
        self.terminateProcessing = False
        self.modelPaths = model_paths_list
        self.imagePaths = image_paths_list
        self.inputPath = input_path
        self.outputPath = output_path
        self.resourcePath = resource_Path
        self.processFinishedCB = processFinishedCB
        self.convertToDDS = convertDDS
        self.convertToASTC = convertASTC
        self.convertToSRGB = convertSRGB

        modelCount = len(model_paths_list)
        self.metaData.headerSizes = [None] * modelCount
        self.metaData.verticeCounts = [None] * modelCount
        self.metaData.indiceCounts = [None] * modelCount

        self.maxThreads = threadCount
    
        self.process_images()
        self.process_models()

    def terminate_conversion(self):
        self.terminateProcessing = True

    def finish_conversion(self):
        if(self.modelPool is not None):
            waitOnClose = True
            while(waitOnClose):
                try:
                    waitOnClose = False
                    self.modelPool.close()
                except:
                    waitOnClose = True
            self.modelPool.join()

        if(self.texturePool is not None):
            waitOnClose = True
            while(waitOnClose):
                try:
                    waitOnClose = False
                    self.texturePool.close()
                except:
                    waitOnClose = True
            self.texturePool.join()

            self.write_metadata()

    def write_metadata(self):
        self.metaData.write_metaData(self.outputPath)

    def process_models(self):

        if(len(self.modelPaths) < self.maxThreads):
            threads = len(self.modelPaths)
        else:
            threads = self.maxThreads

        self.modelPool = ThreadPool(processes = self.maxThreads)
        self.modelPool.map_async(self.convert_model, self.modelPaths)

    def convert_model(self, file):

        listIndex = self.modelPaths.index(file)

        if(self.terminateProcessing):
            self.convert_model_finished(False, "")
            return

        splitted_file = file.split(".")
        splitted_file.pop() # We remove the last element, which is the file ending
        file_name = ''.join(splitted_file)

        inputfile = self.inputPath + "\\"+ file
        outputfile =  self.outputPath + "\\" + file_name + ".ply"

        ms = ml.MeshSet()

        try:
            ms.load_new_mesh(inputfile)
        except:
            self.convert_model_finished(True, "Error opening file: " + inputfile)
            return    

        if(self.terminateProcessing):
            self.convert_model_finished(False, "")
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

        
        if(self.terminateProcessing):
            self.convert_model_finished(False, "")
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

        if(self.terminateProcessing):
            self.convert_model_finished(False, "")
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

        self.convert_model_finished(False, "")    


    def convert_model_finished(self, error, errorText):
        self.processFinishedCB(error, errorText)

    def process_images(self):
        self.texturePool = ThreadPool(processes= self.maxThreads)
        self.texturePool.map_async(self.convert_image, self.imagePaths)

    def convert_image(self, file):

        if(self.terminateProcessing):
            self.processFinishedCB(False, "")
            return

        listIndex = self.imagePaths.index(file)

        splitted_file = file.split(".")
        file_name = splitted_file[0]
        inputfile = self.inputPath + "\\"+ file

        sizeDDS = 0
        sizeASTC = 0

        if(self.convertToDDS):
            outputfileDDS =  self.outputPath + "\\" + file_name + ".dds"
            cmd = self.resourcePath + "texconv " + inputfile + " -o " + self.outputPath + " -m 1 -f DXT1 -y"
            if(self.convertToSRGB):
                cmd += " -srgbo" 
            if(subprocess.run(cmd).returncode != 0):
                self.processFinishedCB(True, "Error converting DDS texture: " + inputfile)
        
        if(self.convertToASTC):
            outputfileASCT =  self.outputPath + "\\" + file_name + ".astc"
            cmd = self.resourcePath + "astcenc -cl " + inputfile + " " + outputfileASCT + " 6x6 -medium"
            if(subprocess.run(cmd).returncode != 0):
                self.processFinishedCB(True, "Error converting ASTC texture: " + inputfile)

        # Write the metadata once per sequence
        if(listIndex == 0):
            if(self.convertToDDS):
                sizeDDS = os.path.getsize(outputfileDDS) - 128 #128 = DDS header size
            if(self.convertToASTC):
                sizeASTC = os.path.getsize(outputfileASCT) - 20 #20 = ASTC header size

            if(len(self.imagePaths) == 1):
                textureMode = Sequence_Metadata.TextureMode.single
            if(len(self.imagePaths) > 1):
                textureMode = Sequence_Metadata.TextureMode.perFrame

            dimensions = self.get_image_dimensions(inputfile)
            self.metaData.set_metadata_texture(self.convertToDDS, self.convertToASTC, dimensions[0], dimensions[1], sizeDDS, sizeASTC, textureMode)


        self.processFinishedCB(False, "")

    def get_image_dimensions(self, filePath):

            pilimg = Image.open(filePath) 
            pilimg.load()
            dimensions = [pilimg.width, pilimg.height]
            pilimg.close()
            return dimensions

    def get_image_gamme_encoded(self, filePath):

        gammaencoded = False

        pilimg = Image.open(filePath)
        pilimg.load()
        
        if("gamma" in pilimg.info):
            gamma = pilimg.info["gamma"]
            if(gamma >= 0.45 and gamma <= 0.46):
                gammaencoded = True

        pilimg.close()
        return gammaencoded

