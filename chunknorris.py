#!/usr/bin/env python

import sys
import os
import mclevel
import mclevelbase
import box

class InvalidDimensionError(RuntimeError): pass

def chunkbox(cPos):
    boxpoint = (cPos[0] << 4, 0, cPos[1] << 4)
    boxsize = (16, 128, 16)
    return box.BoundingBox(boxpoint, boxsize)

class mclevelfixer(object):
    def printUsage(self):
        print "Usage: chunknorris.py WORLDDIR BACKUPDIR..."
        print "You can specify more than one backup, they are tried in order."
        print "Options:"
        print "  -h, --help    You're reading it."
        print "  -n, --nether  Fix the Nether instead of the overworld dimension"
        print "  -e, --end     Fix the End instead of the overworld dimension"

    def printUsageAndQuit(self):
        self.printUsage()
        raise SystemExit

    def loadWorld(self, world, dimension):
        worldpath = os.path.expanduser(world)
        if os.path.exists(worldpath):
            level = mclevel.fromFile(worldpath)
        else:
            level = mclevel.loadWorld(world)
        if dimension is not None:
            if dimension in level.dimensions:
                level = level.dimensions[dimension]
            else:
                raise InvalidDimensionError, "Dimension {0} does not exist".format(dimension)
        return level

    def run(self):
        dimension = None
        worlds = []

        programName = sys.argv.pop(0)

        for arg in sys.argv:
            if arg.lower() in ("-h", "--help"):
                self.printUsageAndQuit()
            elif arg.lower() in ("-n", "--nether"):
                dimension = -1
            elif arg.lower() in ("-e", "--end"):
                dimension = 1
            elif arg[0] == "-":
                raise UsageError, "Unknown option ({0})".format(arg)
            else:
                worlds.append(arg)

        validChunks = set()
        damagedChunks = set()

        # Process main level
        print "Loading main level: {0}".format(worlds[0])
        level = self.loadWorld(worlds[0], dimension)
        print "Main level contains {0} chunks.".format(level.chunkCount)
        for i, cPos in enumerate(level.allChunks, 1):
            box = chunkbox(cPos)
            try:
                ch = level.getChunk(*cPos)
                validChunks.add(cPos)
            except mclevelbase.ChunkMalformed:
                print "Malformed chunk: x={0},y={1},z={2}".format(*box.origin)
                damagedChunks.add(cPos)

        # Delete damaged chunks
        for cPos in damagedChunks:
            box = chunkbox(cPos)
            level.deleteChunksInBox(box)

        # Process backup levels
        for world in worlds[1:]:
            print "Loading backup level: {0}".format(world)
            backup = self.loadWorld(world, dimension)
            print "Backup level contains {0} chunks.".format(backup.chunkCount)
            for i, cPos in enumerate(backup.allChunks, 1):
                if cPos not in validChunks:
                    box = chunkbox(cPos)
                    try:
                        ch = backup.getChunk(*cPos)
                        #At this point, chunk seems to be valid
                        level.copyBlocksFrom(backup, box, box.origin)
                        validChunks.add(cPos)
                        if cPos in damagedChunks:
                            damagedChunks.remove(cPos)
                            print "Malformed chunk replaced with backup chunk: x={0},y={1},z={2}".format(*box.origin)
                        else:
                            print "Missing chunk replaced with backup chunk: x={0},y={1},z={2}".format(*box.origin)
                    except mclevelbase.ChunkMalformed:
                        print "Malformed chunk in backup: x={0},y={1},z={2}".format(*box.origin)
            backup.close()

        # Warn about chunks that are still damaged
        if len(damagedChunks):
            for cPos in damagedChunks:
                box = chunkbox(cPos)
                print "WARNING: Malformed chunk not found in any backup, deleting it: x={0},y={1},z={2}".format(*box.origin)
            print "Enter Y to delete these chunks and save the level."
            print "Enter N to abort."
            answer = raw_input("Delete chunks and save? ")
            if answer.lower() == 'y':
                print "Damaged chunks deleted."
            else:
                print "Aborted."
                level.close()
                return

        # Save level
        print "Relighting..."
        level.generateLights()
        print "Saving level..."
        level.saveInPlace()

        # Repair region files
        print "Repairing regions..."
        if level.version:
            level.preloadRegions()
            for rf in level.regionFiles.itervalues():
                rf.repair()

        # Save level again
        print "Saving level again..."
        level.saveInPlace()
        level.close()

def main(argv):
    mclevelfixer().run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

