from PIL import Image
import tempfile
import shutil
import json
import os
import multiprocessing
import subprocess
import time

__DEBUGMODE__ = False

# Loads the configuration files
with open('config.json') as config_file:
    config = json.load(config_file)

with open('helmets.json') as config_file:
    helmets = json.load(config_file)

def d_Print(str):
    if(__DEBUGMODE__):
        print(str)


def genPlayerHelmets(player, exportDir):
    playerConfig = helmets["Players"][player]
    playerPatches = playerConfig["Patches"]

    print(f"Generating helmets for {player}" + "\n", end='')

    # Initialises the list of texures for the player
    playerConfig["Textures"] = {}
    for camo in config["Templates"]:
        playerConfig["Textures"][camo] = True 

    # Loops through each helmet for the player
    for helmet in playerConfig["Helmets"]:
        helmetConfig = helmets["Types"][helmet]
        
        camo = helmetConfig["Texture"]
        
        # If the texture has already been generated, don't do it again
        if(playerConfig["Textures"][camo]):
           
            d_Print(f"Generating texture {player}:{camo}")
            
            playerConfig["Textures"][camo] = False

            # Loads the configuration for this specific camo pattern
            camoConfig = config["Templates"][camo]

            # Initialises the camoflage texture and formats correctly for merging layers later on
            I_Camo_Load = Image.open(camoConfig["FileName"])
            I_Camo = Image.I_Canvas = Image.new("RGBA", (I_Camo_Load.width, I_Camo_Load.height), None)
            I_Camo.paste(I_Camo_Load)

            # For the camoflage, loops through all the patches and adds them 
            # if there is an applicable texture for the individual player.
            for patch in camoConfig["Patches"]:
                patchConfig = camoConfig["Patches"][patch]
                
                patchPath = playerPatches[ patchConfig["Ref"] ]

                if( patchPath == None ):
                    continue
                
                # Initialise patch canvas and resize it
                I_Canvas = Image.new("RGBA", (I_Camo.width * 2 , I_Camo.height * 2), None)

                I_Patch = Image.open( patchPath )
                I_Patch = I_Patch.resize( 
                    (patchConfig["Size"]["x"] * 2, 
                    patchConfig["Size"]["y"]  * 2)
                )
                
                # Handles flipping if required
                if(patchConfig["FlipX"]):
                    I_Patch = I_Patch.transpose(Image.FLIP_LEFT_RIGHT)
                if(patchConfig["FlipY"]):
                    I_Patch = I_Patch.transpose(Image.FLIP_TOP_BOTTOM)
                

                # Does the offsets
                xOffset = patchConfig["Pos"]["x"] * 2
                yOffset = patchConfig["Pos"]["y"] * 2

                I_Canvas.paste(I_Patch, (
                    xOffset - round(I_Patch.width / 2),
                    yOffset - round(I_Patch.height / 2)
                    ))

                # Once patch is in postion, rotates it by amount specified
                I_Canvas = I_Canvas.rotate(patchConfig["Rot"], center=(xOffset,yOffset))

                # Downscale the image ( this is how antialiasing is done)
                I_Canvas = I_Canvas.resize(
                    (I_Camo.width , I_Camo.height),
                    Image.ANTIALIAS
                )

                I_Camo = Image.alpha_composite(I_Camo, I_Canvas)

            I_Camo.save(exportDir + "/" + camoConfig["ExportPrefix"] + playerConfig["Name"] + camoConfig["ExportSuffix"] + ".png")



if __name__ == '__main__':

    #Used for calculating execution time
    startTime = time.time()

    tempFolderPNG = tempfile.mkdtemp()
    currentFolder = os.path.dirname(os.path.realpath(__file__))
    
    d_Print(tempFolderPNG)
    d_Print(currentFolder)    

    # Loops through each player
    processes = {}

    for playerName in helmets["Players"]:
        processes[playerName] = multiprocessing.Process( target=genPlayerHelmets, args=[playerName, tempFolderPNG] )

    for process in processes:
        processes[process].start()
        #print(process)
    
    # Waits untill all processes are done, a little inefficient, but works :D
    for process in processes:
        #print(process)
        processes[process].join()

    print(f"Generation complete, Time Elapsed:{round(time.time() - startTime, 2)}")
    print("Converting to PAA")
    

    # Converts the temporary PNGs to .paa files
    for filename in os.listdir(tempFolderPNG):
        #print(filename)
        p=subprocess.Popen([ currentFolder + "\\bin\ImageToPAA.exe", tempFolderPNG + "\\" + filename, config["ExportPath"] + "\\" + os.path.splitext(filename)[0] + ".paa"])
    p.wait()

    print("Generating playerhelmets.hpp")
    # Generates the playerhelmets.hpp file
    playerHelmetsHeader = open(currentFolder + "\\Export\playerhelmets.hpp", "w")
    for playerName in helmets["Players"]:
        playerConfig = helmets["Players"][playerName]
        playerHelmets = playerConfig["Helmets"]
        for helmetType in playerHelmets:
            helmetConfig = helmets["Types"][helmetType]
            camoConfig = config["Templates"][helmetConfig["Texture"]]
    
            helmetName  =   helmetConfig["NamePrefix"] + playerName
            helmetDN    =   "\"[CTG] Player Helmet (" + playerName + "/" + camoConfig["CodeDN"] + ")\""
            helmetCamo  =   camoConfig["CodeName"]
            helmetTexture   =   camoConfig["ExportPrefix"] + playerConfig["Name"] + camoConfig["ExportSuffix"]
            helmetTexture   =   "playerhelmets\\" + helmetTexture
            playerHelmetsHeader.write(helmetConfig["Macro"] + "(" + helmetName +","+ helmetDN + "," + helmetCamo + "," + helmetTexture + ");\n")
    
    playerHelmetsHeader.close()

    # Removes temp folder
    shutil.rmtree(tempFolderPNG)

    print(f"Process Complete, Time Elapsed:{round(time.time() - startTime, 2)}")
    