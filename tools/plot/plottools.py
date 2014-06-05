# Python Libraries
from __future__ import print_function
from __future__ import division
import sys
import os
lib_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(lib_path)
import numpy
from scipy.stats import mstats, wilcoxon, mannwhitneyu, rankdata
import time, datetime
import argparse
import HTML
from collections import *
import statsmodels.sandbox.stats.multicomp as sm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import getpass
import fnmatch

# Local Libraries
# Distal Libraries
from rgt.GenomicRegion import *
from rgt.GenomicRegionSet import *
from rgt.ExperimentalMatrix import *
from rgt.Util import *
from rgt.CoverageSet import *

# Local test
dir = os.getcwd()


###########################################################################################
#                    Universal functions 
###########################################################################################
def print2(parameter, string):
    """ Show the message on the console and also save in a list for future backup. """
    print(string)
    parameter.append(string)
    
def unique(a):
    seen = set()
    return [seen.add(x) or x for x in a if x not in seen]
        
def gen_tags(exps, tag):
    """Generate the unique tags from the EM according to the given tag. """
    if tag == "reads":
        try: l = [exps.get_type(i,"factor") for i in exps.get_readsnames()]
        except: 
            print("You must define 'factor' column in experimental matrix for grouping.")
            sys.exit(1)
    elif tag == "regions":
        try: l = [exps.get_type(i,"factor") for i in exps.get_regionsnames()]
        except: 
            print("You must define 'factor' column in experimental matrix for grouping.")
            sys.exit(1)
    else:
        try: l = exps.fieldsDict[tag]
        except: 
            print('Cannot find the column "' + tag +'"')
            sys.exit(1)
    return unique(l)

def colormap(exps, colorby, definedinEM):
    """Generate the self.colors in the format which compatible with matplotlib"""
    if definedinEM:
        if colorby == "reads":
            colors = []
            for i in exps.get_readsnames():
                c = exps.get_type(i,"color")
                if c[0] == "(":
                    rgb = [ eval(j) for j in c.strip('()').split(',')]
                    colors.append(rgb)
                else:
                    colors.append(exps.get_type(i,"color"))
        elif colorby == "regions":
            colors = []
            for i in exps.get_regionsnames():
                c = exps.get_type(i,"color")
                if c[0] == "(":
                    rgb = [ eval(j) for j in c.strip('()').split(',')]
                    colors.append(rgb)
                else:
                    colors.append(exps.get_type(i,"color"))
        else:
            colors = [exps.get_type(i,"color") for i in exps.fieldsDict[colorby]]
    if definedinEM == False:
        #colors = [ 'lightgreen', 'pink', 'cyan', 'lightblue', 'tan', 'orange']
        #colors = plt.cm.jet(numpy.linspace(0.1, 0.9, len(gen_tags(exps, colorby)))).tolist()
        colors = plt.cm.Set1(numpy.linspace(0.1, 0.9, len(gen_tags(exps, colorby)))).tolist()
    return colors

def colormaps(exps, colorby, definedinEM):
    """Generate a list of colormaps in the format which compatible with matplotlib"""
    if definedinEM:
        if colorby == "reads":
            colors = []
            for i in exps.get_readsnames():
                c = exps.get_type(i,"color")
                colors.append(exps.get_type(i,"color"))
        elif colorby == "regions":
            colors = []
            for i in exps.get_regionsnames():
                c = exps.get_type(i,"color")
                colors.append(exps.get_type(i,"color"))
        else:
            colors = [exps.get_type(i,"color") for i in exps.fieldsDict[colorby]]
    if definedinEM == False:
        colors = ['Blues', 'Reds', 'Greens', 'Oranges', 'Purples',  'YlGnBu', 'Greys','gist_yarg', 'GnBu', 
                  'OrRd', 'PuBu', 'PuRd', 'RdPu', 'YlGn', 'BuGn', 'YlOrBr', 'BuPu','YlOrRd','PuBuGn','binary']
    return colors


def output_array(array, directory, folder, filename):
    """ Write a txt file from the given array. """
    pd = os.path.join(dir,directory,folder)
    try:
        os.stat(os.path.dirname(pd))
    except:
        os.mkdir(os.path.dirname(pd))
    try:
        os.stat(pd)
    except:
        os.mkdir(pd)   
             
    f = open(os.path.join(pd,filename),"w")
    for i,line in enumerate(array):
        f.write(("\t".join(j for j in line))+"\n")
    f.close()
###########################################################################################
#                    Projection test
###########################################################################################
class projection:
    def __init__(self, referenceEM, queryEM):
        self.rEM, self.qEM = ExperimentalMatrix(), ExperimentalMatrix()
        self.rEM.read(referenceEM)
        self.qEM.read(queryEM)
        self.references = self.rEM.get_regionsets()
        self.referencenames = self.rEM.get_regionsnames()
        self.query = self.qEM.get_regionsets()
        self.querynames = self.qEM.get_regionsnames()
    
    def group_refque(self, groupby=False):
        self.groupedreference = OrderedDict()  # Store all bed names according to their types
        self.groupedquery = OrderedDict()  # Store all bed names according to their types
        if groupby:
            for r in self.references:
                ty = self.rEM.get_type(r.name,groupby)
                try: self.groupedreference[ty].append(r)
                except: self.groupedreference[ty] =[r]
            
            for q in self.query:
                ty = self.qEM.get_type(q.name,groupby)
            try: self.groupedquery[ty].append(q)
            except: self.groupedquery[ty] =[q]
        else:
            self.groupedreference["All"] = self.references
            self.groupedquery["All"] = self.query
    
    def colors(self, colorby, definedinEM):
        ############# Color #####################################
        self.color_list = colormap(self.qEM, colorby, definedinEM).tolist()
        self.color_tags = gen_tags(self.qEM, colorby)
        self.color_tags.append('Background')
        self.color_list.append('0.70')
    
    def projection_test(self, organism):
        self.qlist = OrderedDict()
        for ty in self.groupedquery.keys():
            self.qlist[ty] = OrderedDict()
            for i, r in enumerate(self.groupedreference[ty]):
                self.qlist[ty][r.name] = OrderedDict()
                for j, q in enumerate(self.groupedquery[ty]):
                    background, ratio, p = r.projection_test(q, organism, extra=True)
                    self.qlist[ty][r.name][q.name] = ratio
                    if p < 0.025: 
                        if len(q) == 0:
                            print("    {0:25s}{1:40s}{2:.2e}\tEmpty query!".format(r.name,q.name,p))
                        else:
                            print("    {0:25s}{1:40s}{2:.2e}\tSignificantly unassociated!".format(r.name,q.name,p))
                    elif p > 0.975:
                        if len(q) == 0:
                            print("    {0:25s}{1:40s}{2:.2e}\tEmpty query!".format(r.name,q.name,p))
                        else:
                            print("    {0:25s}{1:40s}{2:.2e}\tSignificantly associated!".format(r.name,q.name,p))
                    else: print("    {0:25s}{1:40s}{2:.2e}".format(r.name,q.name,p))
                print("    {0:25s}{1:40s}{2:.2e}".format(r.name,"---Coverage in whole genome---", background))
                self.qlist[ty][r.name]['Background'] = background

    def plot(self, logt=None):
        f, ax = plt.subplots()
        if logt:
            ax.set_yscale('log')
        else:
            ax.locator_params(axis = 'y', nbins = 2)
        g_label = []
        for ind_ty, ty in enumerate(self.qlist.keys()):
            g_label.append(ty)
            r_label = []   
            for ind_r,r in enumerate(self.qlist[ty].keys()):
                r_label.append(r)
                width = 0.8/(len(self.qlist[ty][r].keys())+1) # Plus one background
                for ind_q, q in enumerate(self.qlist[ty][r].keys()):
                    x = ind_ty*len(self.qlist[ty].keys())+ ind_r + ind_q*width + 0.1
                    y = self.qlist[ty][r][q]
                    print(x)
                    ax.bar(x, y, width=width, color=self.color_list[ind_q],align='edge')
        ax.set_ylabel("Percentage of associated regions",fontsize=12)
        ax.yaxis.tick_left()
        #ax.set_xlim(-0.2,len(self.qlist.keys())*len(self.qlist.keys())-0.2)
        #ax.set_xticks([i + 0.6 - width for i in range(len(self.groupedreference.keys()))])
        ax.set_xticks([i + 0.5 - 0.5*width for i in range(len(g_label)*len(r_label))])
        ax.set_xticklabels(r_label*len(g_label),rotation=60)
        ax.tick_params(axis='x', which='both', top='off', bottom='off', labelbottom='on')
        ax.legend(self.color_tags, loc='center left', handlelength=1, handletextpad=1, 
                  columnspacing=2, borderaxespad=0., prop={'size':10}, bbox_to_anchor=(1.05, 0.5))
        for spine in ['top', 'right']:  # 'left', 'bottom'
            ax.spines[spine].set_visible(False)
        f.tight_layout(pad=1.08, h_pad=None, w_pad=None)
        self.fig = f

###########################################################################################
#                    Jaccard test
###########################################################################################

###########################################################################################
#                    Boxplot 
###########################################################################################
class boxplot:
    """
    input:
        exps: input experimental matrix
        title: Default = boxplot
        groupby: Group the data by the given factor in the header of experimental matrix
        
    output:
        parameters: list of records
        figs: a list of figure(s)
    """
    def __init__(self,exps, title="Boxplot"):
        # Read the Experimental Matrix
        self.title = title
        self.exps = exps
        self.beds = exps.get_regionsets() # A list of GenomicRegionSets
        self.bednames = exps.get_regionsnames()
        self.reads = exps.get_readsfiles()
        self.readsnames = exps.get_readsnames()
        self.fieldsDict = exps.fieldsDict
        self.parameter = []
    
    def combine_allregions(self):
        all_bed = GenomicRegionSet("All regions")
        for bed in self.beds:
            all_bed.combine(bed)
        all_bed.remove_duplicates() #all_bed is sorted!!
        return all_bed
    
    def bedCoverage(self,bed):
        """ Return coverage matrix of multiple reads on one bed. 
        bed --> GenomicRegionSet
        """
        c=[]
        for rp in self.reads:
            r = os.path.abspath(rp)   # Here change the relative path into absolute path
            cov = CoverageSet(r,bed)
            cov.coverage_from_genomicset(r)
            cov.normRPM()
            c.append(cov.coverage)
            print("    processing: "+rp)
        return numpy.transpose(c)
      
    def quantile_normalization(self,matrix):
        """ Return the np.array which contains the normalized values
        """
        
        rank_matrix = []
        for c in range(matrix.shape[1]):
            col = matrix[:,c]
            rank_col = mstats.rankdata(col)
            rank_matrix.append(rank_col)
    
        ranks = numpy.array(rank_matrix)
        trans_rank = numpy.transpose(ranks)
        
        # Calculate for means of ranks
        print("    Calculating for the mean of ranked data...")
        sort_matrix = numpy.sort(matrix,axis=0)
        means = []
        for r in range(matrix.shape[0]):
            row = [x for x in sort_matrix[r,:]]
            means.append(numpy.mean(row))
    
        # Replace the value by new means
        print("    Replacing the data value by normalized mean...")
        normalized_table = numpy.around(trans_rank)
        for i, v  in enumerate(means):
            normalized_table[normalized_table == i+1] = v
        #print(rounded_rank)
        return normalized_table

    def tables_for_plot(self,norm_table,all_bed):
        """ Return a Dict which stores all tables for each bed with file path(more unique) as its key. """
        tableDict = {} # Storage all tables for each bed with bedname as the key
        conList = []   # Store containers of beds
        iterList = []
        
        for i,bed in enumerate(self.beds):
            tableDict[bed.name] = []
            bed.sort()
            conList.append(bed.__iter__())
            iterList.append(conList[-1].next())
            
        for i, r in enumerate(all_bed.sequences):
            for j in range(len(self.beds)):
                while r > iterList[j]:
                    try:
                        iterList[j] = conList[j].next()
                    except:
                        break
                if r == iterList[j]:
                    tableDict[self.beds[j].name].append(norm_table[i])
                elif r < iterList[j]:
                    continue
        return tableDict

    def group_tags(self, groupby, sortby, colorby):
        """Generate the tags for the grouping of plot
        Parameters:
            groupby = 'reads','regions','cell',or 'factor'
            colorby = 'reads','regions','cell',or 'factor'
            sortby = 'reads','regions','cell',or 'factor'
        """
        if groupby == "None":
            self.group_tags = ["All"]
        else:
            self.group_tags = gen_tags(self.exps, groupby)
        if sortby == "None":
            self.sort_tags = ["All"]
        else:
            self.sort_tags = gen_tags(self.exps, sortby)
        if colorby == "None":
            self.color_tags = ["All"]
        else:
            self.color_tags = gen_tags(self.exps, colorby)

    def group_data(self, tables):  
        plotDict = OrderedDict()  # Extracting the data from different bed_bams file
        cues = OrderedDict()   # Storing the cues for back tracking
        for bedname in tables.keys():
            plotDict[bedname] = {}
            mt = numpy.array(tables[bedname])
            for i,readname in enumerate(self.readsnames):
                plotDict[bedname][readname] = mt[:,i]
                #print(plotDict[bedname][readname])
                x = tuple(self.exps.get_types(readname) + self.exps.get_types(bedname))
                cues[x] = [bedname, readname]
        #print(cues.keys())
        sortDict = {}  # Storing the data by sorting tags
        for g in self.group_tags:
            #print("    "+g)
            sortDict[g] = {}
            for a in self.sort_tags:
                #print("        "+c)
                sortDict[g][a] = {}
                for c in self.color_tags:
                    #print("            "+a)
                    sortDict[g][a][c] = []
                    for k in cues.keys():
                        if set([g,a,c]).difference(set(['All'])) <= set(k):
                            sortDict[g][a][c] = plotDict[cues[k][0]][cues[k][1]]
        self.sortDict = sortDict

    def color_map(self, colorby, definedinEM):
        self.colors = colormap(self.exps, colorby, definedinEM)
        
    def plot(self, title, html=False, logT=False):
        """ Return boxplot from the given tables.
        
        """
        f, axarr = plt.subplots(1, len(self.group_tags), dpi=300, sharey = True)
        canvas = FigureCanvas(f)
        canvas.set_window_title(title)
        try: axarr = axarr.reshape(-1)
        except: axarr = [axarr]
        plt.subplots_adjust(bottom=0.3)
        if logT:
            axarr[0].set_ylabel("Count number (log)")
        else:
            axarr[0].set_ylabel("Count number")
        for i, g in enumerate(self.group_tags):
            axarr[i].set_title(g, y=0.94)
            if logT:
                axarr[i].set_yscale('log')
            axarr[i].tick_params(axis='y', direction='out')
            axarr[i].yaxis.tick_left()
            axarr[i].yaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.7, zorder=1)
            d = []  # Store data within group
            color_t = []  # Store tag for coloring boxes
            x_ticklabels = []  # Store ticklabels
            for k, a in enumerate(self.sort_tags):
                for j, c in enumerate(self.color_tags):
                    if self.sortDict[g][a][c] == []:  # When there is no matching data, skip it
                        continue
                    else:
                        d.append([x+1 for x in self.sortDict[g][a][c]])
                        color_t.append(self.colors[j])
                        x_ticklabels.append(a)  #  + "." + c
            # Fine tuning boxplot
            bp = axarr[i].boxplot(d, notch=False, sym='o', vert=True, whis=1.5, positions=None, widths=None, 
                                  patch_artist=True, bootstrap=None)
            z = 10 # zorder for bosplot
            plt.setp(bp['whiskers'], color='black',linestyle='-',linewidth=0.8,zorder=z)
            plt.setp(bp['fliers'], markerfacecolor='gray',color='none',alpha=0.3,markersize=1.8,zorder=z)
            plt.setp(bp['caps'],color='none',zorder=z)
            plt.setp(bp['medians'], color='black', linewidth=1.5,zorder=z+1)
            legends = []
            for patch, color in zip(bp['boxes'], color_t):
                patch.set_facecolor(color) # When missing the data, the color patch will exceeds
                patch.set_zorder(z)
                legends.append(patch)
                
            # Fine tuning subplot
            axarr[i].set_xticks([len(self.color_tags)*n + 1 + (len(self.color_tags)-1)/2 for n,s in enumerate(self.sort_tags)])
            #plt.xticks(xlocations, sort_tags, rotation=90, fontsize=10)
            axarr[i].set_xticklabels(self.sort_tags, rotation=0, fontsize=10)
            
            axarr[i].set_ylim(bottom=0.95)
            for spine in ['top', 'right', 'left', 'bottom']:
                axarr[i].spines[spine].set_visible(False)
            axarr[i].tick_params(axis='x', which='both', bottom='off', top='off', labelbottom='on')
            
            if i > 0:
                plt.setp(axarr[i].get_yticklabels(),visible=False)
                #plt.setp(axarr[i].get_yticks(),visible=False)
                axarr[i].minorticks_off()
                axarr[i].tick_params(axis='y', which='both', left='off', right='off', labelbottom='off')
                    
        plt.setp([a.get_yticklabels() for a in axarr[1:]], visible=False)
        #plt.legend(colors, color_tags, loc=7)
        axarr[-1].legend(legends[0:len(self.color_tags)], self.color_tags, loc='center left', handlelength=1, 
                 handletextpad=1, columnspacing=2, borderaxespad=0., prop={'size':10},
                 bbox_to_anchor=(1.05, 0.5))
        f.tight_layout(pad=2, h_pad=None, w_pad=None)
        self.fig = f
        
    def gen_html(self,outputname, title, pvalue):
        ########## HTML ###################
        pd = os.path.join(dir,outputname,title)
        try:
            os.stat(os.path.dirname(pd))
        except:
            os.mkdir(os.path.dirname(pd))
        try:
            os.stat(pd)
        except:
            os.mkdir(pd)    
        f = open(os.path.join(pd,'boxplot.html'),'w')
        table = []
        # Header
        table.append(['<font size="7">' + title + "</font>"])
        # Each row is a plot with its data
        table.append(["<img src='boxplot.png' width=800 >"])
        
        #### Calculate p value ####
            
        for g in self.group_tags:
            table.append(['<font size="5">' + g + "</font>"])
            indM = 0
            header = []
            data_p = []
            arr = []
            
            for s in self.sort_tags:
                for c in self.color_tags:
                    header.append("{0}.{1}".format(s,c))
                    data_p.append(self.sortDict[g][s][c])

                    for i, d in enumerate(data_p[:indM]):
                        u, p_value = mannwhitneyu(data_p[indM], d)
                        arr.append(p_value)
                    indM = indM + 1
            #print(len(arr))
            [h,pc,a,b] = sm.multipletests(arr, alpha=pvalue, returnsorted=False)
            ar = numpy.chararray([len(self.color_tags)*len(self.sort_tags),len(self.color_tags)*len(self.sort_tags)], itemsize=10)
            ar[:] = "-"
            k = 0
            for c in self.color_tags:
                for s in self.sort_tags:
                    for i, d in enumerate(header[:k]):
                        ar[k,i] = "{:3.1e}".format(pc[0.5*k*(k-1) + i])
                    k = k + 1
                        
            nrows, ncols = ar.shape
            subtable = '<style>table,th,td{border:1px solid black;border-collapse:collapse;text-align:center;table-layout: fixed;font-size:8pt;}\
            </style><table style="width:800px">'
            for r in range(nrows+1):
                subtable += '<tr>'
                for c in range(ncols+1):
                    if r == 0:
                        if c == 0: subtable += '<td><i>p-value</i></td>'
                        elif c > 0: subtable += '<td>'+header[c-1]+'</td>'
                    if r > 0:
                        if c == 0: subtable += '<td>'+header[r-1]+'</td>'
                        elif c > 0:
                            #print(r,"  ",c,"   ", int(0.5*(r-1)*(r-2) + c -1))
                            if c < r and h[int(0.5*(r-1)*(r-2) + c -1)]:
                                subtable += '<td><font color="red">'+ar[r-1,c-1]+'</font></td>'
                            else: subtable += '<td>'+ar[r-1,c-1]+'</td>'
                subtable += '</tr>'
            subtable += '</table>'
            table.append([subtable])
        table.append(["<a href='"+os.path.join(dir, outputname,title,"parameters.log")+" '><font size="+'"5"'+">Parameters</a>"])
        htmlcode = HTML.table(table)
        for line in htmlcode: f.write(line)
        f.close()

###########################################################################################
#                    Lineplot 
###########################################################################################

class lineplot:
    def __init__(self,exps, title, center, extend, rs, bs, ss):
        # Read the Experimental Matrix
        self.title = title
        self.exps = exps
        self.beds = exps.get_regionsets() # A list of GenomicRegionSets
        self.bednames = exps.get_regionsnames()
        self.reads = exps.get_readsfiles()
        self.readsnames = exps.get_readsnames()
        self.fieldsDict = exps.fieldsDict
        self.parameter = []
        self.center = center
        self.extend = extend
        self.rs = rs
        self.bs = bs
        self.ss = ss
    
    def relocate_bed(self):
        processed_beds = []
        processed_bedsF = [] # Processed beds to be flapped
        for bed in self.beds:
            if self.center == 'bothends':
                newbed = bed.relocate_regions(center='leftend', left_length=self.extend, right_length=self.extend+int(0.5*self.bs))
                processed_beds.append(newbed)
                newbedF = bed.relocate_regions(center='rightend', left_length=self.extend+int(0.5*self.bs), right_length=self.extend)
                processed_bedsF.append(newbedF)
            else:
                newbed = bed.relocate_regions(center=self.center, left_length=self.extend, right_length=self.extend+int(0.5*self.bs))
                processed_beds.append(newbed)
        self.processed_beds = processed_beds
        self.processed_bedsF = processed_bedsF
        
    def group_tags(self, groupby, sortby, colorby):
        """Generate the tags for the grouping of plot
        Parameters:
            groupby = 'reads','regions','cell',or 'factor'
            colorby = 'reads','regions','cell',or 'factor'
            sortby = 'reads','regions','cell',or 'factor'
        """
        if groupby == "None":
            self.group_tags = ["All"]
        else:
            self.group_tags = gen_tags(self.exps, groupby)
        if sortby == "None":
            self.sort_tags = ["All"]
        else:
            self.sort_tags = gen_tags(self.exps, sortby)
        if colorby == "None":
            self.color_tags = ["All"]
        else:
            self.color_tags = gen_tags(self.exps, colorby)
    
    def gen_cues(self):
        self.cuebed = {}
        self.cuebam = {}
        for bed in self.bednames:
            self.cuebed[bed] = set(self.exps.get_types(bed))
        for bam in self.readsnames:
            self.cuebam[bam] = set(self.exps.get_types(bam))
        
    def coverage(self, sortby, heatmap=False, logt=False):
        # Calculate for coverage
        data = OrderedDict()
        totn = len(self.sort_tags) * len(self.group_tags) * len(self.color_tags)
        bi = 0
        for s in self.sort_tags:
            data[s] = OrderedDict()
            for g in self.group_tags:
                data[s][g] = OrderedDict()
                for c in self.color_tags:
                    for bed in self.cuebed.keys():
                        if len(set([g,s,c]).intersection(self.cuebed[bed])) == 2:
                            for bam in self.cuebam.keys():
                                if len(set([g,s,c]).intersection(self.cuebam[bam])) == 2:
                                    ts = time.time()
                                    #data[s][g][c] = []
                                    i = self.bednames.index(bed)
                                    j = self.readsnames.index(bam)
                                    cov = CoverageSet(bed+"."+bam, self.processed_beds[i])
                                    cov.coverage_from_bam(self.reads[j], read_size = self.rs, binsize = self.bs, stepsize = self.ss)
                                    # When bothends, consider the fliping end
                                    if self.center == 'bothends':
                                        flap = CoverageSet("for flap", self.processed_bedsF[i])
                                        flap.coverage_from_bam(self.reads[j], read_size = self.rs, binsize = self.bs, stepsize = self.ss)
                                        ffcoverage = numpy.fliplr(flap.coverage)
                                        cov.coverage = numpy.concatenate((cov.coverage, ffcoverage), axis=0)
                                    # Averaging the coverage of all regions of each bed file
                                    if heatmap:
                                        if logt:
                                            data[s][g][c] = numpy.log10(numpy.vstack(cov.coverage)) # Store the array into data list
                                        else:
                                            data[s][g][c] = numpy.vstack(cov.coverage) # Store the array into data list
                                    else:
                                        avearr = numpy.array(cov.coverage)
                                        avearr = numpy.average(avearr, axis=0)
                                        numpy.transpose(avearr)
                                        data[s][g][c] = avearr # Store the array into data list
                                    bi += 1
                                    te = time.time()
                                    print2(self.parameter, "     Computing ("+ str(bi)+"/"+str(totn)+")\t" + "{0:40}   --{1:<6.1f}secs".format(bed+"."+bam, ts-te))
        self.data = data
        
    def colormap(self, colorby, definedinEM):
        self.colors = colormap(self.exps, colorby, definedinEM)
        
    def plot(self, groupby, colorby, output, printtable=False):
        rot = 50
        ticklabelsize = 7
        f, axs = plt.subplots(len(self.data.keys()),len(self.data.values()[0]), dpi=300) # figsize=(8.27, 11.69)
        if len(self.data.keys()) == 1 and len(self.data.values()[0]) == 1: axs=[axs]
    
        for it, s in enumerate(self.data.keys()):
            for i,g in enumerate(self.data[s].keys()):
                if it == 0: axs[it,i].set_title(g,fontsize=11)
                # Processing for future output
                if printtable:
                    pArr = numpy.array(["Name","X","Y"]) # Header
                    
                for j, c in enumerate(self.data[s][g].keys()): 
                    y = self.data[s][g][c]
                    x = numpy.linspace(-self.extend, self.extend, len(y))
                    axs[it, i].plot(x,y, color=self.colors[j], lw=1)
                    # Processing for future output
                    if printtable:
                        [bed] = [bed for bed in self.bednames if [g,c,s] in self.cuebed[bed]]
                        name = numpy.array(*len(x))
                        xvalue = numpy.array(x)
                        yvalue = numpy.array(y)
                        conArr = numpy.vstack([name,xvalue,yvalue])
                        conArr = numpy.transpose(conArr)
                        pArr = numpy.vstack([pArr, conArr])
                if printtable:
                    [bam] = [bam for bam in self.readsnames if [g,c,s] in self.cuebam[bam]]
                    output_array(pArr, directory = output, folder ="lineplot_tables",filename=s+"_"+bam)
                
                axs[it,i].set_xlim([-self.extend, self.extend])
                plt.setp(axs[it, i].get_xticklabels(), fontsize=ticklabelsize, rotation=rot)
                plt.setp(axs[it, i].get_yticklabels(), fontsize=ticklabelsize)
                axs[it, i].locator_params(axis = 'x', nbins = 4)
                axs[it, i].locator_params(axis = 'y', nbins = 4)
                axs[0,-1].legend(self.color_tags, loc='center left', handlelength=1, handletextpad=1, columnspacing=2, borderaxespad=0., prop={'size':10}, bbox_to_anchor=(1.05, 0.5))
                
        for i,ty in enumerate(self.data.keys()):
            axs[i,0].set_ylabel("{}".format(ty),fontsize=12, rotation=90)
        f.tight_layout(pad=1.08, h_pad=None, w_pad=None)
        self.fig = f

    def gen_html(self,outputname, title):
        ########## HTML ###################
        pd = os.path.join(dir,outputname,title)
        try:
            os.stat(os.path.dirname(pd))
        except:
            os.mkdir(os.path.dirname(pd))
        try:
            os.stat(pd)
        except:
            os.mkdir(pd)    
        f = open(os.path.join(pd,'lineplot.html'),'w')
        table = []
        # Header 
        table.append(['<style>table{border:1px solid black;border-collapse:collapse;text-align:center;table-layout: fixed;font-size:8pt;}\
            </style><font size="7">' + title + "</font>"])
        # Each row is a plot with its data
        table.append(["<img src='lineplot.png' width=800 >"])
        table.append(["<a href='"+os.path.join(dir, outputname,title,"parameters.log")+" '><font size="+'"5"'+">Parameters</a>"])
        htmlcode = HTML.table(table)
        for line in htmlcode: f.write(line)
        f.close()
                    
    def hmsort(self,sort):
        if sort == None:
            pass
        elif sort == 0:
            for t in self.data.keys():
                for i, g in enumerate(self.data[t].keys()):
                    #print(numpy.sum(data[t][bed].values()[0], axis=1))
                    #print(len(numpy.sum(data[t][bed].values()[0], axis=1)))
                    
                    sumarr = numpy.sum([numpy.sum(d, axis=1) for d in self.data[t][g].values()], axis=0)
                    #print(sumarr)
                    #sumarr = numpy.sum(sumarr, axis=1)
                    ind = stats.rankdata(sumarr,method='ordinal') # The index for further sorting
                    #numpy.fliplr(ind)
                    
                    for j, c in enumerate(self.data[t][g].keys()):
                        d = numpy.empty(shape=(self.data[t][g][c].shape))
                        for k, ranki in enumerate(ind):
                            d[-ranki,:] = self.data[t][g][c][k,:]
                        self.data[t][g][c] = d
        else:
            for t in self.data.keys():
                for i, g in enumerate(self.data[t].keys()):
                    sumarr = numpy.sum(self.data[t][g].values()[sort - 1], axis=1)
                    #print(sumarr)
                    #sumarr = numpy.sum(sumarr, axis=1)
                    ind = stats.rankdata(sumarr,method='ordinal') # The index for further sorting
                    #list(ind)
                    #print(ind)
                    for j, c in enumerate(self.data[t][g].keys()):
                        d = numpy.empty(shape=(self.data[t][g][c].shape))
                        for k, ranki in enumerate(ind):
                            d[-ranki,:] = self.data[t][g][c][k,:]
                        self.data[t][g][c] = d
                    #print(data[t][bed].values()[0])
    
    def hmcmlist(self, colorby, definedinEM):
        self.colors = colormaps(self.exps, colorby, definedinEM)
    
    def heatmap(self, logt):
        tickfontsize = 6
        ratio = 6
        self.hmfiles = []
        self.figs = []
        for ti, t in enumerate(self.data.keys()):
            #fig.append(plt.figure())
            #rows = len(data[t].keys())
            columns = len(self.data[t].values()[0].keys())
            #fig, axs = plt.subplots(rows,columns, sharey=True, dpi=300)
            #matplotlib.pyplot.subplots_adjust(left=1, right=2, top=2, bottom=1)
            fig = plt.figure(t)
            plt.suptitle("Heatmap: "+t, y=1.05)
            rows = len(self.data[t].keys())
            
            
            #gs = gridspec.GridSpec(rows*ratio,columns)
            axs = numpy.empty(shape=(rows+1,columns), dtype=object)
    
            for bi, g in enumerate(self.data[t].keys()):
                for bj, c in enumerate(self.data[t][g].keys()):
                    max_value = numpy.amax(self.data[t][g][c])
                    axs[bi, bj] = plt.subplot2grid(shape=(rows*ratio+1, columns), loc=(bi*ratio, bj), rowspan=ratio)
                    if bi == 0: axs[bi, bj].set_title(c, fontsize=7)
                    im = axs[bi, bj].imshow(self.data[t][g][c], extent=[-self.extend, self.extend, 0,1], aspect='auto', vmin=0, vmax=max_value, interpolation='nearest', cmap=self.colors[bj])
                    axs[bi, bj].set_xlim([-self.extend, self.extend])
                    axs[bi, bj].set_xticks([-self.extend, 0, self.extend])
                    #axs[bi, bj].set_xticklabels([-args.e, 0, args.e]
                    plt.setp(axs[bi, bj].get_xticklabels(), fontsize=tickfontsize, rotation=0)
                    #plt.setp(axs[bi, bj].get_yticklabels(), fontsize=10)
                    #axs[bi, bj].locator_params(axis = 'x', nbins = 2)
                    #axs[bi, bj].locator_params(axis = 'y', nbins = 4)
                    for spine in ['top', 'right', 'left', 'bottom']:
                        axs[bi, bj].spines[spine].set_visible(False)
                    axs[bi, bj].tick_params(axis='x', which='both', bottom='off', top='off', labelbottom='on')
                    axs[bi, bj].tick_params(axis='y', which='both', left='off', right='off', labelleft='off')
                    #if bj > 0:
                    #    plt.setp(axs[bi, bj].get_yticklabels(),visible=False)
                    #plt.setp(axarr[i].get_yticks(),visible=False)
                    axs[bi, bj].minorticks_off()
                    if bj == 0:
                        #nregion = len(self.exps.objectsDict[g])
                        #axs[bi, bj].set_ylabel(self.exps.get_type(g,'factor')+" ("+str(nregion) + ")", fontsize=7)
                        axs[bi, bj].set_ylabel(g, fontsize=7)
                    if bi == rows-1:
                        #divider = make_axes_locatable(axs[bi,bj])
                        #cax = divider.append_axes("bottom", size="5%", pad=0.5)
                        axs[rows,bj] = plt.subplot2grid((rows*ratio+1, columns), (rows*ratio, bj))
                        axs[rows,bj].tick_params(axis='y', which='both', left='off', right='off', labelleft='off')
                        
                        #cbar = grid.cbar_axes[i//2].colorbar(im)
                        cbar = plt.colorbar(im, cax = axs[bi+1,bj], ticks=[0, max_value], orientation='horizontal')
                        cbar.outline.set_linewidth(0.5)
                        cbar.ax.xaxis.set_ticks_position('none')
                        if logt:
                            cbar.ax.set_xticklabels(['0', '{:1.1f}'.format(max_value)], fontsize=tickfontsize)# horizontal colorbar
                            cbar.set_label('log10', fontsize=tickfontsize)
                        else:
                            cbar.ax.set_xticklabels(['0', int(max_value)], fontsize=tickfontsize)# horizontal colorbar
                        #cbar.set_label('Amplitute of signal')
            fig.tight_layout(pad=1, h_pad=1, w_pad=1)
            self.figs.append(fig)
            self.hmfiles.append("heatmap"+ "_" + t)
    
    def gen_htmlhm(self, outputname, title):
        ########## HTML ###################
        pd = os.path.join(dir,outputname,title)
        try:
            os.stat(os.path.dirname(pd))
        except:
            os.mkdir(os.path.dirname(pd))
        try:
            os.stat(pd)
        except:
            os.mkdir(pd)    
        f = open(os.path.join(pd,'heatmap.html'),'w')
        table = []
        # Header 
        table.append(['<style>table{border:1px solid black;border-collapse:collapse;text-align:center;table-layout: fixed;font-size:8pt;}\
            </style><font size="7">' + title + "</font>"])
        # Each row is a plot with its data
        for name in self.hmfiles:
            table.append(["<img src='" + name + ".png' width=800 >"])
        table.append(["<a href='"+os.path.join(dir, outputname,title,"parameters.log")+" '><font size="+'"5"'+">Parameters</a>"])
        htmlcode = HTML.table(table)
        for line in htmlcode: f.write(line)
        f.close()
        
    
###########################################################################################
#                    Heatmap 
###########################################################################################
class heatmap:
    
    def __init__(self,exps, title="Boxplot"):
        pass







