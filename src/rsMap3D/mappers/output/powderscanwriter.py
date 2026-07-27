"""
Copyright (c) 2017 UChicago Argonne, LLC
See LICENSE file.
"""

import logging

logger = logging.getLogger(__name__)
import inspect

# ===== ZZ
# import matplotlib
# matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import numpy as np

from rsMap3D.gui.rsm3dcommonstrings import EMPTY_STR

X_COORD_OPTIONS = ["tth", "q"]
Y_SCALING_OPTIONS = ["Linear", "log"]
# =====
FILENAME_MERGE_STR = "%s_S%03d.xye"


class PowderScanWriter:
    def __init__(self):
        self.gridData = None
        self.numPoints = None
        self.fileInfo = []
        self.outputFileName = None
        # ===== add x-axis label "q/tth" and y_scale "Linear/log", ZZ 2020/03/03
        self.xlabel = X_COORD_OPTIONS[0]
        self.yscale = Y_SCALING_OPTIONS[0]
        # =====

    def setData(self, x, y, e):
        self.gridData = np.transpose(np.array([x, y, e]))
        self.fileInfo = []

    def setFileInfo(self, fileInfo):
        if (fileInfo is None) or (len(fileInfo) == 0):
            raise ValueError(
                self.whatFunction()
                + "passed no filename information."
                + "requires a tuple with six members:\n"
                + "1. project filename so that a filename can be"
                + "constructed if filename is blank\n"
                + "2. User filename\n"
                + "3. number of datapints\n"
                + "4. outputFileName\n"
                + "5. x-axis label\n"
                + "6. y-axis lin/log"
            )  # ===== ZZ
        elif len(fileInfo) != 6:
            raise ValueError(
                self.whatFunction()
                + "passed no filename information."
                + "requires a tuple with six members:\n"
                + "1. project filename so that a filename can be"
                + "constructed if filename is blank\n"
                + "2. User filename\n"
                + "3. number of datapints\n"
                + "4. outputFileName\n"
                + "5. x-axis label\n"
                + "6. y-axis lin/log"
            )  # ===== ZZ
        self.fileInfo.append(fileInfo[0])
        self.fileInfo.append(fileInfo[1])
        self.numPoints = fileInfo[2]
        self.outputFileName = fileInfo[3]
        # ===== ZZ
        self.xlabel = fileInfo[4]
        self.yscale = fileInfo[5]
        # =====

    # ===== Add this really rudimentry plot function here, ZZ
    def plot(self):
        logger.debug(f"fileInfo[0] {self.fileInfo[0]}, fileInfo[1] {self.fileInfo[1]}")
        if self.outputFileName == EMPTY_STR or self.outputFileName is None:
            outputFileName = FILENAME_MERGE_STR % (self.fileInfo[0], self.fileInfo[1])
        else:
            outputFileName = self.outputFileName
        logger.debug(f"outputFileName {outputFileName} ")

        data = self.gridData
        fig, ax = plt.subplots()
        ax.plot(data[:, 0], data[:, 1], marker=".", label=outputFileName)
        ax.set_ylabel("Intensity [arb. units]", fontsize=14, color="red")

        if self.yscale is Y_SCALING_OPTIONS[1]:
            ax.set_yscale("log")
        else:
            ax.set_yscale("linear")
        if self.xlabel is X_COORD_OPTIONS[0]:
            ax.set_xlabel(r"$2 \theta$ [deg]", fontsize=14, color="red")
        else:
            ax.set_xlabel("Q (A^-1)", fontsize=14, color="red")
        ax.set_title("Powder diffraction curves")
        ax.autoscale(enable=True, axis="x", tight=True)
        ax.legend()

        # plt.show()
        plt.show(block=False)
        plt.pause(2)
        # plt.close()

    # =====

    def write(self):
        logger.debug(f"fileInfo[0] {self.fileInfo[0]}, fileInfo[1] {self.fileInfo[1]}")
        if self.outputFileName == EMPTY_STR or self.outputFileName is None:
            outputFileName = FILENAME_MERGE_STR % (self.fileInfo[0], self.fileInfo[1])
        else:
            outputFileName = self.outputFileName
        logger.debug(f"outputFileName {outputFileName} ")
        with open(outputFileName, "w") as outFile:
            outFile.write(f"# SPECfile={self.fileInfo[0]}\n")
            outFile.write(f"# Scan Numbers={self.fileInfo[1]}\n")
            outFile.write("# Instrument configuration=%s\n")
            outFile.write("# Detector Configuration=%s\n")
            outFile.write("# Bad Pixel File %s")
            outFile.write("#\n")
            logger.debug(f"self.gridData {self.gridData}")
            logger.debug(f"self.gridData.shape {str(self.gridData.shape)}")
            outFile.write(f"# x_min = {self.gridData[0][0]:.4f}\n")
            outFile.write(f"# x_max = {self.gridData[-1][0]:.4f}\n")
            x_step = (self.gridData[-1][0] - self.gridData[0][0]) / self.numPoints
            outFile.write(f"# x_step = {x_step:.4f}\n")
            outFile.write("# x_npts = %d\n" % self.numPoints)
            #            outFile.write("# Wavelength = %.6f\n" % self.wavelength)
            outFile.write("# Temperature = n/a\n")
            outFile.write("# \n")
            # ===== Put the correct X-label in the file header, ZZ
            if self.xlabel == X_COORD_OPTIONS[0]:
                outFile.write("# TwoTheta ")
            else:
                outFile.write("#     Q    ")
            # =====
            outFile.write("Intensity Error\n")
            np.savetxt(outFile, self.gridData, fmt="%10.6e %10.6e %10.6e")

    def whatFunction(self):
        return inspect.stack()[1][3]
