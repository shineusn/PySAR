#!/usr/bin/env python3
############################################################
# Program is part of PySAR                                 #
# Copyright(c) 2018, Zhang Yunjun                          #
# Author:  Zhang Yunjun, Nov 2018                          #
############################################################


import os
import sys
import argparse
import h5py
import numpy as np
import matplotlib.pyplot as plt
from pysar.objects import ifgramStack
from pysar.utils import readfile, plot as pp
from pysar import view


###########################  Sub Function  #############################
EXAMPLE = """example:
  plot_coherence_matrix.py  INPUTS/ifgramStack.h5  --yx 277 1069
  plot_coherence_matrix.py  INPUTS/ifgramStack.h5  --yx 277 1069  --map-file velocity.h5 --map-plot-cmd 'view.py {} --wrap --wrap-range -3 3 --sub-x 900 1400 --sub-y 0 500'
"""

def create_parser():
    parser = argparse.ArgumentParser(description='Display Network of Interferograms',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=EXAMPLE)

    parser.add_argument('ifgram_file', help='interferogram stack file')
    parser.add_argument('--yx', type=int, metavar=('Y', 'X'), nargs=2, 
                        help='Point of interest X coordinate')
    parser.add_argument('-c','--cmap', dest='colormap', default='truncate_RdBu',
                        help='Colormap for coherence matrix')

    parser.add_argument('--map-file', dest='map_file', default='velocity.h5',
                        help='dataset to show in map to facilitate point selection')
    parser.add_argument('--map-plot-cmd', dest='map_plot_cmd', default='view.py {} --wrap',
                        help='view.py command to plot the input map file')

    parser.add_argument('--save', dest='save_fig',
                        action='store_true', help='save the figure')
    parser.add_argument('--nodisplay', dest='disp_fig',
                        action='store_false', help='save and do not display the figure')
    return parser


def cmd_line_parse(iargs=None):
    parser = create_parser()
    inps = parser.parse_args(args=iargs)
    if not inps.disp_fig:
        inps.save_fig = True
    return inps


def read_network_info(inps):
    k = readfile.read_attribute(inps.ifgram_file)['FILE_TYPE']
    if k != 'ifgramStack':
        raise ValueError('input file {} is not ifgramStack: {}'.format(inps.ifgram_file, k))

    obj = ifgramStack(inps.ifgram_file)
    obj.open()
    inps.date12_list    = obj.get_date12_list(dropIfgram=False)
    date12_kept = obj.get_date12_list(dropIfgram=True)
    inps.ex_date12_list = sorted(list(set(inps.date12_list) - set(date12_kept)))
    inps.date_list = obj.get_date_list(dropIfgram=False)
    print('number of all     interferograms: {}'.format(len(inps.date12_list)))
    print('number of dropped interferograms: {}'.format(len(inps.ex_date12_list)))
    print('number of kept    interferograms: {}'.format(len(inps.date12_list) - len(inps.ex_date12_list)))
    print('number of acquisitions: {}'.format(len(inps.date_list)))

    if not inps.yx:
        inps.yx = (obj.refY, obj.refX)
        print('plot initial coherence matrix at reference pixel: {}'.format(inps.yx))
    return inps


def plot_coherence_matrix4one_pixel(yx, fig, ax, inps):
    # read coherence
    box = (yx[1], yx[0], yx[1]+1, yx[0]+1)
    coh = readfile.read(inps.ifgram_file, datasetName='coherence', box=box)[0].tolist()
    # prep metadata
    plotDict = {}
    plotDict['fig_title'] = 'Y = {}, X = {}'.format(yx[0], yx[1])
    plotDict['colormap'] = inps.colormap
    # plot
    ax = pp.plot_coherence_matrix(ax, inps.date12_list, coh, inps.ex_date12_list, plotDict)[0]
    fig.canvas.draw()
    # info
    print('-'*30)
    print('pixel: yx = {}'.format(yx))
    print('min/max coherence: {:.2f} / {:.2f}'.format(np.min(coh), np.max(coh)))
    return ax


##########################  Main Function  ##############################
global ax2
def main(iargs=None):
    inps = cmd_line_parse(iargs)
    if not inps.disp_fig:
        plt.switch_backend('Agg')

    # read network info
    inps = read_network_info(inps)

    # Figure 1 - map
    fig1, ax1 = plt.subplots(num=inps.map_file)
    cmd = inps.map_plot_cmd.format(inps.map_file)
    data1, atr, inps1 = view.prep_slice(cmd)
    ax1 = view.plot_slice(ax1, data1, atr, inps1)[0]

    # Figure 2 - coherence matrix
    fig2, ax2 = plt.subplots(num='Coherence Matrix')
    if inps.yx:
        plot_coherence_matrix4one_pixel(inps.yx, fig2, ax2, inps)

    def plot_event(event):
        if event.inaxes == ax1:
            yx = (int(event.ydata+0.5), int(event.xdata+0.5))
            plot_coherence_matrix4one_pixel(yx, fig2, ax2, inps)

    if inps.save_fig:
        plt.savefig('coh_mat_{}'.format())

    # Final linking of the canvas to the plots.
    cid = fig1.canvas.mpl_connect('button_press_event', plot_event)
    if inps.disp_fig:
        plt.show()
    fig1.canvas.mpl_disconnect(cid)
    return


############################################################
if __name__ == '__main__':
    main()
