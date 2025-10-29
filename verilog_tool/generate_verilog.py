import json
import pprint
import os
import sys

from VectorCGRA.cgra.translate.CGRATemplateRTL_test import *
# from VectorCGRA.cgra.test.CgraTemplateRTL_test import *

CONFIG_MEM_SIZE = 8
DATA_MEM_SIZE = 4

xbarTypeList = ["W", "E", "N", "S", "NE", "NW", "SE", "SW"]
fuTypeList = ["Phi", "Add", "Shift", "Ld", "Sel", "Cmp", "MAC", "St", "Ret", "Mul", "Logic", "Br"]

xbarType2Port = {}
xbarType2Port["W"] = PORT_WEST
xbarType2Port["E"] = PORT_EAST
xbarType2Port["N"] = PORT_NORTH
xbarType2Port["S"] = PORT_SOUTH
xbarType2Port["NE"] = PORT_NORTHEAST
xbarType2Port["NW"] = PORT_NORTHWEST
xbarType2Port["SE"] = PORT_SOUTHEAST
xbarType2Port["SW"] = PORT_SOUTHWEST

xbarPort2Type = {}
xbarPort2Type[PORT_WEST] = "W"
xbarPort2Type[PORT_EAST] = "E"
xbarPort2Type[PORT_NORTH] = "N"
xbarPort2Type[PORT_SOUTH] = "S"
xbarPort2Type[PORT_NORTHEAST] = "NE"
xbarPort2Type[PORT_NORTHWEST] = "NW"
xbarPort2Type[PORT_SOUTHEAST] = "SE"
xbarPort2Type[PORT_SOUTHWEST] = "SW"

xbarPortOpposites = {}
xbarPortOpposites[PORT_WEST] = PORT_EAST
xbarPortOpposites[PORT_EAST] = PORT_WEST
xbarPortOpposites[PORT_NORTH] = PORT_SOUTH
xbarPortOpposites[PORT_SOUTH] = PORT_NORTH
xbarPortOpposites[PORT_NORTHWEST] = PORT_SOUTHEAST
xbarPortOpposites[PORT_NORTHEAST] = PORT_SOUTHWEST
xbarPortOpposites[PORT_SOUTHWEST] = PORT_NORTHEAST
xbarPortOpposites[PORT_SOUTHEAST] = PORT_NORTHWEST

class ParamTile:
    def __init__(s, ID, dimX, dimY, posX, posY, tileWidth, tileHeight):
        s.ID = ID
        s.disabled = False
        s.posX = posX
        s.posY = posY
        s.dimX = dimX
        s.dimY = dimY
        s.width = tileWidth
        s.height = tileHeight
        s.outLinks = {}
        s.inLinks = {}
        s.neverUsedOutPorts = set()
        s.fuDict = {}
        s.xbarDict = {}
        s.mapping = {}

        for i in range(PORT_DIRECTION_COUNTS):
            s.neverUsedOutPorts.add(i)

        for xbarType in xbarTypeList:
            s.xbarDict[xbarType] = 0

        for fuType in fuTypeList:
            s.fuDict[fuType] = 1

    def hasFromMem(s):
        for link in s.inLinks.values():
            if not link.disabled and link.isFromMem():
                return True
        return False

    def hasToMem(s):
        for link in s.outLinks.values():
            if not link.disabled and link.isToMem():
                return True
        return False

    def getInvalidInPorts(s):
        invalidInPorts = set()
        for port in range(PORT_DIRECTION_COUNTS):
            if port not in s.inLinks:
                invalidInPorts.add(port)
                continue
            link = s.inLinks[port]
            if link.disabled or type(link.srcTile) == ParamSPM or link.srcTile.disabled:
                invalidInPorts.add(port)
                continue
        return invalidInPorts

    def isDefaultFus(s):
        for fuType in fuTypeList:
            if s.fuDict[fuType] != 1:
                return False
        return True

    def getAllValidFuTypes(s):
        fuTypes = set()
        for fuType in fuTypeList:
            if s.fuDict[fuType] == 1:
                if fuType == "Ld" or fuType == "St":
                    fuTypes.add("Ld")
                else:
                    fuTypes.add(fuType)
        return list(fuTypes)

    def getInvalidOutPorts(s):
        invalidOutPorts = set()
        for port in range(PORT_DIRECTION_COUNTS):
            if port not in s.outLinks:
                invalidOutPorts.add(port)
                continue
            link = s.outLinks[port]
            if link.disabled or type(link.dstTile) == ParamSPM or link.dstTile.disabled:
                invalidOutPorts.add(port)
                continue
        return invalidOutPorts

    def reset(s):
        s.disabled = False
        s.mapping = {}

        for i in range(PORT_DIRECTION_COUNTS):
            s.neverUsedOutPorts.add(i)

        for xbarType in xbarTypeList:
            s.xbarDict[xbarType] = 0

        for fuType in fuTypeList:
            s.fuDict[fuType] = 1

    def resetOutLink(s, portType, link):
        s.outLinks[portType] = link
        s.xbarDict[xbarPort2Type[portType]] = 1
        if portType in s.neverUsedOutPorts:
            s.neverUsedOutPorts.remove(portType)

    def resetInLink(s, portType, link):
        s.inLinks[portType] = link

    def setOutLink(s, portType, link):
        s.outLinks[portType] = link

    def setInLink(s, portType, link):
        s.resetInLink(portType, link)

    # position X/Y for drawing the tile
    def getPosXY(s, baseX=0, baseY=0):
        return (baseX + s.posX, baseY + s.posY)

    # position X/Y for connecting routing ports
    def getPosXYOnPort(s, portType, baseX=0, baseY=0):
        if portType == PORT_NORTH:
            return s.getNorth(baseX, baseY)
        elif portType == PORT_SOUTH:
            return s.getSouth(baseX, baseY)
        elif portType == PORT_WEST:
            return s.getWest(baseX, baseY)
        elif portType == PORT_EAST:
            return s.getEast(baseX, baseY)
        elif portType == PORT_NORTHEAST:
            return s.getNorthEast(baseX, baseY)
        elif portType == PORT_NORTHWEST:
            return s.getNorthWest(baseX, baseY)
        elif portType == PORT_SOUTHEAST:
            return s.getSouthEast(baseX, baseY)
        else:
            return s.getSouthWest(baseX, baseY)

    def getNorthWest(s, baseX=0, baseY=0):
        return (baseX + s.posX, baseY + s.posY)

    def getNorthEast(s, baseX=0, baseY=0):
        return (baseX + s.posX + s.width, baseY + s.posY)

    def getSouthWest(s, baseX=0, baseY=0):
        return (baseX + s.posX, baseY + s.posY + s.height)

    def getSouthEast(s, baseX=0, baseY=0):
        return (baseX + s.posX + s.width, baseY + s.posY + s.height)

    def getWest(s, baseX=0, baseY=0):
        return (baseX + s.posX, baseY + s.posY + s.height // 2)

    def getEast(s, baseX=0, baseY=0):
        return (baseX + s.posX + s.width, baseY + s.posY + s.height // 2)

    def getNorth(s, baseX=0, baseY=0):
        return (baseX + s.posX + s.width // 2, baseY + s.posY)

    def getSouth(s, baseX=0, baseY=0):
        return (baseX + s.posX + s.width // 2, baseY + s.posY + s.height)

    def getDimXY(s):
        return s.dimX, s.dimY

    def getIndex(s, tileList):
        if s.disabled:
            return -1
        index = 0
        for tile in tileList:
            if tile.dimY < s.dimY and not tile.disabled:
                index += 1
            elif tile.dimY == s.dimY and tile.dimX < s.dimX and not tile.disabled:
                index += 1
        return index


class ParamSPM:
    def __init__(s, posX, numOfReadPorts, numOfWritePorts):
        s.posX = posX
        s.ID = -1
        s.numOfReadPorts = numOfReadPorts
        s.numOfWritePorts = numOfWritePorts
        s.disabled = False
        s.inLinks = {}
        s.outLinks = {}

    def getNumOfValidReadPorts(s):
        ports = 0
        for physicalPort in range(s.numOfReadPorts):
            if physicalPort not in s.inLinks:
                continue
            if s.inLinks[physicalPort].disabled:
                continue
            ports += 1
        return ports

    def getNumOfValidWritePorts(s):
        ports = 0
        for physicalPort in range(s.numOfWritePorts):
            if physicalPort not in s.outLinks:
                continue
            if s.outLinks[physicalPort].disabled:
                continue
            ports += 1
        return ports

    def getValidReadPort(s, logicalPort):
        port = 0
        for physicalPort in range(logicalPort + 1):
            if physicalPort not in s.inLinks:
                continue
            if s.inLinks[physicalPort].disabled:
                continue
            if physicalPort == logicalPort:
                return port
            port += 1
        return -1

    def getValidWritePort(s, logicalPort):
        port = 0
        for physicalPort in range(logicalPort + 1):
            if physicalPort not in s.outLinks:
                continue
            if s.outLinks[physicalPort].disabled:
                continue
            if physicalPort == logicalPort:
                return port
            port += 1
        return -1

    def getPosX(s, baseX):
        return s.posX + baseX

    def setInLink(s, portType, link):
        s.inLinks[portType] = link

    def resetInLink(s, portType, link):
        s.setInLink(portType, link)

    def setOutLink(s, portType, link):
        s.outLinks[portType] = link

    def resetOutLink(s, portType, link):
        s.setOutLink(portType, link)


class ParamLink:
    def __init__(s, srcTile, dstTile, srcPort, dstPort):
        s.srcTile = srcTile
        s.dstTile = dstTile
        s.srcPort = srcPort
        s.dstPort = dstPort
        s.disabled = False
        s.srcTile.resetOutLink(s.srcPort, s)
        s.dstTile.resetInLink(s.dstPort, s)
        s.mapping = set()

    def getMemReadPort(s):
        if s.isFromMem():
            spm = s.srcTile
            return spm.getValidReadPort(s.srcPort)
        return -1

    def getMemWritePort(s):
        if s.isToMem():
            spm = s.dstTile
            return spm.getValidWritePort(s.dstPort)
        return -1

    def isToMem(s):
        return type(s.dstTile) == ParamSPM

    def isFromMem(s):
        return type(s.srcTile) == ParamSPM

    def getSrcXY(s, baseX=0, baseY=0):
        if type(s.srcTile) != ParamSPM:
            return s.srcTile.getPosXYOnPort(s.srcPort, baseX, baseY)
        else:
            dstPosX, dstPosY = s.dstTile.getPosXYOnPort(s.dstPort, baseX, baseY)
            spmPosX = s.srcTile.getPosX(baseX)
            return spmPosX, dstPosY

    def getDstXY(s, baseX=0, baseY=0):
        if type(s.dstTile) != ParamSPM:
            return s.dstTile.getPosXYOnPort(s.dstPort, baseX, baseY)
        else:
            srcPosX, srcPosY = s.srcTile.getPosXYOnPort(s.srcPort, baseX, baseY)
            spmPosX = s.dstTile.getPosX(baseX)
            return spmPosX, srcPosY

class ParamCGRA:
    def __init__(s, rows, columns, configMemSize=CONFIG_MEM_SIZE, dataMemSize=DATA_MEM_SIZE):
        s.rows = rows
        s.columns = columns
        s.configMemSize = configMemSize
        s.dataMemSize = dataMemSize
        s.tiles = []
        s.templateLinks = []
        s.updatedLinks = []
        s.targetTileID = 0
        s.dataSPM = None
        s.targetAppName = "   Not selected yet"
        s.compilationDone = False
        s.verilogDone = False
        s.targetKernels = []
        s.targetKernelName = None
        s.DFGNodeCount = -1
        s.resMII = -1
        s.recMII = -1

    # return error message if the model is not valid
    def getErrorMessage(s):
        # at least one tile can perform mem acess
        memExist = False
        # at least one tile exists
        tileExist = False
        for tile in s.tiles:
            if not tile.disabled:
                tileExist = True
                # a tile contains at least one FU
                fuExist = False
                # the tile connect to mem need to able to access mem
                if tile.hasToMem() or tile.hasFromMem():
                    # for now, the compiler doesn't support seperate read or write, both of them need to locate in the same tile
                    if tile.hasToMem() and tile.hasFromMem() and tile.fuDict["Ld"] == 1 and tile.fuDict["St"] == 1:
                        memExist = True
                    else:
                        return "Tile " + str(tile.ID) + " needs to contain the Load/Store functional units."

                for fuType in fuTypeList:
                    if tile.fuDict[fuType] == 1:
                        fuExist = True
                if not fuExist:
                    return "At least one functional unit needs to exist in tile " + str(tile.ID) + "."

        if not tileExist:
            return "At least one tile needs to exist in the CGRA."

        if not memExist:
            return "At least one tile including a Load/Store functional unit needs to directly connect to the data SPM."

        return ""

    def getValidTiles(s):
        validTiles = []
        for tile in s.tiles:
            if not tile.disabled:
                validTiles.append(tile)
        return validTiles

    def getValidLinks(s):
        validLinks = []
        for link in s.updatedLinks:
            if not link.disabled and not link.srcTile.disabled and not link.dstTile.disabled:
                validLinks.append(link)
        return validLinks

    def updateFuXbarPannel(s):
        targetTile = s.getTileOfID(s.targetTileID)
        for fuType in fuTypeList:
            if fuType in fuCheckVars:
                fuCheckVars[fuType].set(targetTile.fuDict[fuType])

        for xbarType in xbarTypeList:
            if xbarType in xbarCheckVars:
                xbarCheckVars[xbarType].set(targetTile.xbarDict[xbarType])

    def initDataSPM(s, dataSPM):
        s.dataSPM = dataSPM

    def updateMemSize(s, configMemSize, dataMemSize):
        s.configMemSize = configMemSize
        s.dataMemSize = dataMemSize

    def initTiles(s, tiles):
        for r in range(s.rows):
            for c in range(s.columns):
                s.tiles.append(tiles[r][c])

    def addTile(s, tile):
        s.tiles.append(tile)

    def initTemplateLinks(s, links):
        numOfLinks = s.rows * s.columns * 2 + (s.rows - 1) * s.columns * 2 + (s.rows - 1) * (s.columns - 1) * 2 * 2

        for link in links:
            s.templateLinks.append(link)

    def resetTiles(s):

        for tile in s.tiles:
            tile.reset()

            for fuType in fuTypeList:
                fuCheckVars[fuType].set(tile.fuDict[fuType])
                fuCheckbuttons[fuType].configure(state="normal")

            for xbarType in xbarTypeList:
                xbarCheckVars[xbarType].set(tile.xbarDict[xbarType])
                xbarCheckbuttons[xbarType].configure(state="normal")

    def enableAllTemplateLinks(s):
        for link in s.templateLinks:
            link.disabled = False

    def resetLinks(s):
        for link in s.templateLinks:
            link.disabled = False
            link.srcTile.resetOutLink(link.srcPort, link)
            link.dstTile.resetInLink(link.dstPort, link)
            link.mapping = set()

        s.updatedLinks = s.templateLinks[:]

        for portType in range(PORT_DIRECTION_COUNTS):
            if portType in s.getTileOfID(s.targetTileID).neverUsedOutPorts:
                xbarCheckbuttons[xbarPort2Type[portType]].configure(state="disabled")

    def addTemplateLink(s, link):
        s.templateLinks.append(link)

    def addUpdatedLink(s, link):
        s.updatedLinks.append(link)

    def removeUpdatedLink(s, link):
        s.updatedLinks.remove(link)
        # src = link.srcTile
        # src.xbarDict[link.srcPort] = 0

    def updateFuCheckbutton(s, fuType, value):
        tile = s.getTileOfID(s.targetTileID)
        tile.fuDict[fuType] = value

    def updateXbarCheckbutton(s, xbarType, value):
        tile = s.getTileOfID(s.targetTileID)
        tile.xbarDict[xbarType] = value
        port = xbarType2Port[xbarType]
        if port in tile.outLinks:
            tile.outLinks[port].disabled = True if value == 0 else False

    def getTileOfID(s, ID):
        for tile in s.tiles:
            if tile.ID == ID:
                return tile
        return None

    def getTileOfDim(s, dimX, dimY):
        for tile in s.tiles:
            if tile.dimX == dimX and tile.dimY == dimY:
                return tile
        return None

    # tiles could be disabled due to the disabled links
    def updateTiles(s):
        unreachableTiles = set()
        for tile in s.tiles:
            unreachableTiles.add(tile)

        for link in s.updatedLinks:
            if link.disabled == False and type(link.dstTile) == ParamTile:
                if link.dstTile in unreachableTiles:
                    unreachableTiles.remove(link.dstTile)
                    if len(unreachableTiles) == 0:
                        break

        for tile in unreachableTiles:
            tile.disabled = True

    def getUpdatedLink(s, srcTile, dstTile):
        for link in s.updatedLinks:
            if link.srcTile == srcTile and link.dstTile == dstTile:
                return link
        return None

    # TODO: also need to consider adding back after removing...
    def updateLinks(s):
        needRemoveLinks = set()
        for link in s.updatedLinks:
            if link.disabled:
                needRemoveLinks.add((link.srcTile, link.dstTile))

        for link in s.templateLinks:
            link.srcTile.setOutLink(link.srcPort, link)
            link.dstTile.setInLink(link.dstPort, link)
        s.updatedLinks = s.templateLinks[:]

        for tile in s.tiles:
            if tile.disabled:
                for portType in tile.outLinks:
                    outLink = tile.outLinks[portType]
                    dstNeiTile = outLink.dstTile
                    oppositePort = xbarPortOpposites[portType]
                    if oppositePort in tile.inLinks:
                        inLink = tile.inLinks[oppositePort]
                        srcNeiTile = inLink.srcTile

                        # some links can be fused as single one due to disabled tiles
                        if not inLink.disabled and not outLink.disabled and inLink in s.updatedLinks and outLink in s.updatedLinks:
                            updatedLink = ParamLink(srcNeiTile, dstNeiTile, inLink.srcPort, outLink.dstPort)
                            s.addUpdatedLink(updatedLink)
                            s.removeUpdatedLink(inLink)
                            s.removeUpdatedLink(outLink)
                        # links that are disabled need to be removed
                        if inLink.disabled and inLink in s.updatedLinks:
                            s.removeUpdatedLink(inLink)
                        if outLink.disabled and outLink in s.updatedLinks:
                            s.removeUpdatedLink(outLink)

                    else:
                        if outLink in s.updatedLinks:
                            s.removeUpdatedLink(outLink)

                for portType in tile.outLinks:
                    outLink = tile.outLinks[portType]
                    if outLink in s.updatedLinks:
                        s.removeUpdatedLink(outLink)

                for portType in tile.inLinks:
                    inLink = tile.inLinks[portType]
                    if inLink in s.updatedLinks:
                        s.removeUpdatedLink(inLink)

        for link in s.updatedLinks:
            if (link.srcTile, link.dstTile) in needRemoveLinks:
                link.disabled = True
                if type(link.srcTile) == ParamTile:
                    link.srcTile.xbarDict[xbarPort2Type[link.srcPort]] = 0

    def updateSpmOutlinks(s):
        spmOutlinksSwitches = widgets['spmOutlinksSwitches']
        spmConfigPannel = widgets["spmConfigPannel"]
        for switch in spmOutlinksSwitches:
            switch.destroy()
        for port in paramCGRA.dataSPM.outLinks:
            switch = customtkinter.CTkSwitch(spmConfigPannel, text=f"link {port}", command=switchDataSPMOutLinks)
            if not paramCGRA.dataSPM.outLinks[port].disabled:
                switch.select()
            switch.pack(pady=(5, 10))
            spmOutlinksSwitches.insert(0, switch)


ROWS = 2
COLS = 2
CONFIG_MEM_SIZE = 8
DATA_MEM_SIZE = 64

MEM_WIDTH = 50
TILE_HEIGHT = 70
TILE_WIDTH = 70
LINK_LENGTH = 40
GRID_WIDTH = (TILE_WIDTH + LINK_LENGTH) * COLS - LINK_LENGTH
GRID_HEIGHT = (TILE_HEIGHT + LINK_LENGTH) * ROWS - LINK_LENGTH
padHeight = TILE_HEIGHT + LINK_LENGTH
padWidth = TILE_WIDTH + LINK_LENGTH


def get_rows_cols_configmem_from_json_old(filename="cgra-architecture.json"):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f).get("data")
    arch = data.get("architecture", {})
    kernel = data.get("kernel", "/WORK_REPO/CGRA-Flow/kernel.cpp")
    unroll_count = int(data.get("unroll_count", 0))
    vectorizationMode = data.get("vectorizationMode", "none")
    # Force vectorizationMode to "none" if unroll is applied
    if unroll_count == 0 or unroll_count == 1:
        vectorizationMode = "none"
    interconnect = data.get("architecture", {}).get("interconnect", "mesh")
    
    tile_array = arch.get("tile_array", "1x1")
    try:
        rows, cols = map(int, tile_array.lower().split("x"))
    except Exception:
        rows, cols = 1, 1
    
    config_mem_kb = arch.get("config_mem_kb", 8)
    data_spm_kb = arch.get("data_spm_kb", 64)

    tiles = arch.get("tiles", {})

    fu_counts = {}
    for tile in tiles:
        fus = tile.get('functional_units', [])
        for fu in fus:
            fu_counts[fu] = fu_counts.get(fu, 0) + 1

    return rows, cols, config_mem_kb, tiles, kernel, unroll_count, vectorizationMode, interconnect, data, fu_counts, data_spm_kb


def get_rows_cols_configmem_from_json(filename="cgra-architecture.json"):
    with open(filename, "r", encoding="utf-8") as f:
        candidate = json.load(f)
    tile_size = candidate.get('tile_size')
    interconnect = candidate.get("interconnect", "kingmesh")
    paramCGRA_configMemSize = candidate.get('config_mem')
    data_spm_kb = candidate.get('data_spm_kb')
    unroll_count = candidate.get('unroll_factor')
    vectorizationMode = candidate.get('vectorize')
    fus = candidate.get('FUs')

    try:
        paramCGRA_rows, paramCGRA_columns = map(int, tile_size.lower().split("x"))
    except Exception:
        paramCGRA_rows, paramCGRA_columns = 1, 1

    paramCGRA_tiles = {}
    for tile_name, fu_list in fus.items():
        try:
            tile_id = int(tile_name.replace("tile", ""))
        except ValueError:
            continue
        if len(fu_list) == 0 or (len(fu_list) == 1 and fu_list[0]=="Div"):
            print(f"fu_list is empty or Div, add Ret for now~~~~~~~~~~~")
            fu_list = ["Ret"]
        paramCGRA_tiles[tile_id] = fu_list
    
    # Add Ld and St to leftmost tiles in each row if not present
    for row in range(paramCGRA_rows):
        leftmost_tile_id = row * paramCGRA_columns
        if leftmost_tile_id in paramCGRA_tiles:
            fu_list = paramCGRA_tiles[leftmost_tile_id]
            if "Ld" not in fu_list:
                print(f">>> Add Ld for {leftmost_tile_id}")
                fu_list.append("Ld")
            if "St" not in fu_list:
                print(f">>> Add St for {leftmost_tile_id}")
                fu_list.append("St")
    

    print(f"""tile_size: {tile_size}, \n
              paramCGRA_rows: {paramCGRA_rows}, paramCGRA_columns: {paramCGRA_columns}, \n
              interconnect: {interconnect}, \n
              paramCGRA_configMemSize: {paramCGRA_configMemSize}, \n
              data_spm_kb: {data_spm_kb}, \n
              unroll_count: {unroll_count}, \n
              vectorizationMode: {vectorizationMode}, \n
              ------------------------""")

    return paramCGRA_rows, paramCGRA_columns, paramCGRA_configMemSize, paramCGRA_tiles, None, unroll_count, vectorizationMode, interconnect, None, None, data_spm_kb


def process_single_arch(arch_filename):
    # set default arch filename for testing
    if arch_filename == None or arch_filename == "":
        arch_filename = "./kingmesh_True/arch_sample_970.json_latnrm.c_kingmesh_2x2_True_result.json"
    print("Using architecture file:", arch_filename)

    print("Removes CGRATemplateRTL__*.v first")
    os.system("rm -f CGRATemplateRTL__*.v")

    # get file name without path and suffix
    filename_no_path = os.path.basename(arch_filename)
    filename_no_suffix = os.path.splitext(filename_no_path)[0]

    paramCGRA_rows, paramCGRA_columns, paramCGRA_configMemSize, paramCGRA_tiles, kernel, unroll_count, vectorizationMode, interconnect, source_arch, fu_counts, data_spm_kb = get_rows_cols_configmem_from_json(arch_filename)
    print("CGRA Architecture: rows x cols = ", paramCGRA_rows, "x", paramCGRA_columns, ", paramCGRA_configMemSize =", paramCGRA_configMemSize, "kernel =", kernel)
    print("tiles: ")
    # print tiles in a pretty way
    pprint.pprint(paramCGRA_tiles)
    print("tile 0")
    pprint.pprint(paramCGRA_tiles[0])

    print("Functional Unit counts across all tiles: ")
    pprint.pprint(fu_counts)

    # construct CGRA
    print("Generating ParamCGRA...")
    ROWS = paramCGRA_rows
    COLS = paramCGRA_columns
    CONFIG_MEM_SIZE = paramCGRA_configMemSize
    DATA_MEM_SIZE = data_spm_kb
    paramCGRA = ParamCGRA(ROWS, COLS, configMemSize=CONFIG_MEM_SIZE, dataMemSize=DATA_MEM_SIZE)
    print("Rows:", paramCGRA.rows, "Cols:", paramCGRA.columns, "ConfigMemSize:", paramCGRA.configMemSize, "DataMemSize:", paramCGRA.dataMemSize)

    # construct data SPM
    print("Generating Data SPM...")
    if paramCGRA.dataSPM == None:
        print("---------------- Generating Data SPM")
        dataSPM = ParamSPM(MEM_WIDTH, paramCGRA.rows, paramCGRA.columns)
        paramCGRA.initDataSPM(dataSPM)

    # construct tiles
    print("Generating Tiles...")
    tiles = []
    # construct tiles
    if len(paramCGRA.tiles) == 0:
        for i in range(ROWS):
            for j in range(COLS):
                ID = i * COLS + j
                posX = padWidth * j + MEM_WIDTH + LINK_LENGTH
                posY = GRID_HEIGHT - padHeight * i - TILE_HEIGHT

                tile = ParamTile(ID, j, i, posX, posY, TILE_WIDTH, TILE_HEIGHT)
                paramCGRA.addTile(tile)


    print("tiles type:", type(paramCGRA.tiles), "tiles len:", len(paramCGRA.tiles))
    print("tiles[0] type:", type(paramCGRA.tiles[0]), "tiles[0] ID:", paramCGRA.tiles[0].ID)

    # construct template links
    print("Generating Template Links...")
    if len(paramCGRA.templateLinks) == 0:
        for i in range(ROWS):
            for j in range(COLS):
                if j < COLS - 1:
                    # horizontal
                    tile0 = paramCGRA.getTileOfDim(j, i)
                    tile1 = paramCGRA.getTileOfDim(j + 1, i)
                    link0 = ParamLink(tile0, tile1, PORT_EAST, PORT_WEST)
                    link1 = ParamLink(tile1, tile0, PORT_WEST, PORT_EAST)
                    paramCGRA.addTemplateLink(link0)
                    paramCGRA.addTemplateLink(link1)

                if i < ROWS - 1 and j < COLS - 1:
                    # diagonal left bottom to right top
                    tile0 = paramCGRA.getTileOfDim(j, i)
                    tile1 = paramCGRA.getTileOfDim(j + 1, i + 1)
                    link0 = ParamLink(tile0, tile1, PORT_NORTHEAST, PORT_SOUTHWEST)
                    link1 = ParamLink(tile1, tile0, PORT_SOUTHWEST, PORT_NORTHEAST)
                    paramCGRA.addTemplateLink(link0)
                    paramCGRA.addTemplateLink(link1)

                if i < ROWS - 1 and j > 0:
                    # diagonal left top to right bottom
                    tile0 = paramCGRA.getTileOfDim(j, i)
                    tile1 = paramCGRA.getTileOfDim(j - 1, i + 1)
                    link0 = ParamLink(tile0, tile1, PORT_NORTHWEST, PORT_SOUTHEAST)
                    link1 = ParamLink(tile1, tile0, PORT_SOUTHEAST, PORT_NORTHWEST)
                    paramCGRA.addTemplateLink(link0)
                    paramCGRA.addTemplateLink(link1)

                if i < ROWS - 1:
                    # vertical
                    tile0 = paramCGRA.getTileOfDim(j, i)
                    tile1 = paramCGRA.getTileOfDim(j, i + 1)
                    link0 = ParamLink(tile0, tile1, PORT_NORTH, PORT_SOUTH)
                    link1 = ParamLink(tile1, tile0, PORT_SOUTH, PORT_NORTH)
                    paramCGRA.addTemplateLink(link0)
                    paramCGRA.addTemplateLink(link1)

                if j == 0:
                    # connect to memory
                    print(f"--------  connect to memory  --------row:{i} <-> col:{j}")
                    tile0 = paramCGRA.getTileOfDim(j, i)
                    link0 = ParamLink(tile0, paramCGRA.dataSPM, PORT_WEST, i)
                    link1 = ParamLink(paramCGRA.dataSPM, tile0, i, PORT_WEST)
                    paramCGRA.addTemplateLink(link0)
                    paramCGRA.addTemplateLink(link1)

    paramCGRA.updateLinks()

    # update fu
    # old
    # for idx, tile_data in enumerate(paramCGRA_tiles):
    #     print(f"idx: {idx}, tile_data: {tile_data}")
    #     tile = paramCGRA.tiles[idx]
    #     fus = tile_data.get('functional_units', [])
    #     # reset all fus to 0
    #     for fuType in fuTypeList:
    #         tile.fuDict[fuType] = 0
    #     for fu in fus:
    #         tile.fuDict[fu] = 1

    for idx, tile_data in enumerate(paramCGRA_tiles):
        tile = paramCGRA.tiles[idx]
        fus = paramCGRA_tiles[tile_data]
        print(f"idx: {idx}, fus: {fus}")
        # reset all fus to 0
        for fuType in fuTypeList:
            tile.fuDict[fuType] = 0
        for fu in fus:
            tile.fuDict[fu] = 1

    # paramCGRA.tiles[0].fuDict = {'Phi': 0, 'Add': 0, 'Shift': 0, 'Ld': 1, 'Sel': 1, 'Cmp': 1, 'MAC': 1, 'St': 1, 'Ret': 1, 'Mul': 1, 'Logic': 1, 'Br': 1}

    # print all tiles
    for tile in paramCGRA.tiles:
        # print("Tile ID:", tile.ID, "Dim:", (tile.dimX, tile.dimY), "outLinks:", tile.outLinks.keys(), "fus:", tile.fuDict, "xbars:", tile.xbarDict, "disabled:", tile.disabled, "inLinks:", tile.inLinks.keys())
        print("Tile ID:", tile.ID, "Dim:", (tile.dimX, tile.dimY), "fus:", tile.fuDict)
        
        
    print("templateLinks type:", type(paramCGRA.templateLinks), "templateLinks len:", len(paramCGRA.templateLinks))
    # print all template links
    for link in paramCGRA.templateLinks:
        print("Link srcTile:", link.srcTile.ID if type(link.srcTile) == ParamTile else "SPM", 
              "dstTile:", link.dstTile.ID if type(link.dstTile) == ParamTile else "SPM", 
              "srcPort:", link.srcPort, "dstPort:", link.dstPort, "isFromMem:", link.isFromMem(), "isToMem:", link.isToMem(), "disabled:", link.disabled)

    print("Generating Verilog...")
    # cmdline_opts = {'test_verilog': 'zeros', 'test_yosys_verilog': '', 'dump_textwave': False, 'dump_vcd': False,
    #                 'dump_vtb': False, 'max_cycles': None}
    # test_cgra_universal(cmdline_opts, paramCGRA)
    test_cgra_universal(paramCGRA)

    # move the generated verilog file to design.v
    os.system(f"mv CGRATemplateRTL__*.v {filename_no_suffix}.v")

    # convert SystemVerilog to Verilog using sv2v
    print("Converting SystemVerilog to Verilog using sv2v...")
    os.system(f"~/LLM4CGRA/verilog_tool/sv2v/bin/sv2v {filename_no_suffix}.v > ./verilog/{filename_no_suffix}_sv2v.v")

    return f"{filename_no_suffix}_sv2v.v"

if __name__ == "__main__":
    input_file = sys.argv[1]
    print(f"input_file: {input_file}")
    if input_file == "":
        input_file = "./cgra_2x2_design.json"
    result_file = process_single_arch(input_file)

    if result_file:
        # 将结果文件名输出到标准输出（供Bash捕获）
        print(result_file)
    else:
        sys.exit(1)

    # directory_path = "./kingmesh_True"
    # for filename in os.listdir(directory_path):
    #     if filename.endswith('.json'):
    #         file_path = os.path.join(directory_path, filename)
    #         print(f"处理文件: {file_path}")
    #         process_single_arch(file_path)
    #         print(f"Finished processing file: {file_path}\n-----------------------\n")
    

