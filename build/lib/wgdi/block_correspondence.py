import re
import sys

import numpy as np
import pandas as pd
import wgdi.base as base


class block_correspondence():
    def __init__(self, options):
        self.block_len = 0
        self.correspondence = 'all'
        self.position = 'order'
        self.tandem = "True"
        for k, v in options:
            setattr(self, str(k), v)
            print(k, ' = ', v)
        self.homo = [float(k) for k in self.homo.split(',')]

    def run(self):
        lens1 = base.newlens(self.lens1, self.position)
        lens2 = base.newlens(self.lens2, self.position)
        gff1 = base.newgff(self.gff1)
        gff2 = base.newgff(self.gff2)
        gff1 = gff1[gff1['chr'].isin(lens1.index)]
        gff2 = gff2[gff2['chr'].isin(lens2.index)]
        colinearity = base.read_colinearscan(self.colinearity)
        if self.correspondence == 'all':
            cor = [[k, i, 0, lens1[i], j, 0, lens2[j], float(self.homo[0]), float(self.homo[1])]
                   for k in range(1, int(self.wgd)+1) for i in lens1.index for j in lens2.index]
            cor = pd.DataFrame(
                cor, columns=['sub', 'chr1', 'start1', 'end1', 'chr2', 'start2', 'end2', 'homo1', 'homo2'])
            cor.to_csv('all.coor.txt', header=None, index=False)
        else:
            cor = pd.read_csv(self.correspondence, sep=',',
                              header=None, engine='python')
            cor.columns = ['sub', 'chr1', 'start1',
                           'end1', 'chr2', 'start2', 'end2', 'homo1', 'homo2']
        cor['chr1'] = cor['chr1'].astype(str)
        cor['chr2'] = cor['chr2'].astype(str)
        gff1 = pd.concat([gff1, pd.DataFrame(columns=list('L'+str(i)
                                                          for i in range(1, int(self.wgd)+1)))], sort=True)
        if self.tandem in ['True', 'true', '1']:
            colinearity,rm_tandem = self.remove_tandem(colinearity, gff1, gff2)
        a=[[colinearity[i][0],rm_tandem[i]] for i in range(len(colinearity)) if len(rm_tandem[i])>0]
        print(a)
        # align = self.colinearity_region(
        #     gff1, gff2, colinearity, cor, homopairs)
        # align[gff1.columns[-int(self.wgd):]
        #       ].to_csv(self.savefile, sep='\t', header=None)

    def remove_tandem(self, colinearity, gff1, gff2):
        newcolinearity, rm_tandem = [], []
        for k in colinearity:
            block, tandem_loc, n = [], [], -1
            if k[1][0][0] not in gff1.index or k[1][0][2] not in gff2.index:
                continue
            chr1, chr2 = gff1.loc[k[1][0][0], 'chr'], gff2.loc[k[1][0][2], 'chr']
            if chr1 != chr2:
                newcolinearity.append(k)
                rm_tandem.append([])
                continue
            for v in k[1]:
                n += 1
                if base.tandem(chr1, chr2, v[1], v[3]):
                    tandem_loc.append(n)
                    continue
                block.append(v)
            rm_tandem.append(tandem_loc)
            newcolinearity.append([k[0],block,k[1]])
        return newcolinearity, rm_tandem

    def colinearity_region(self, gff1, gff2, colinearity, cor, homopairs):
        for k in colinearity:
            if len(k[0]) <= int(self.block_len):
                continue
            chr1, chr2 = gff1.loc[k[0][0][0], 0], gff2.loc[k[0][0][2], 0]
            array1, array2 = [float(i[1]) for i in k[0]], [
                float(i[3]) for i in k[0]]
            start1, end1 = min(array1), max(array1)
            start2, end2 = min(array2), max(array2)
            if (end1-start1)/len(array1) <= 0.05 or (end2-start2)/len(array2) <= 0.05:
                continue
            newcor = cor[(cor['chr1'] == str(chr1)) &
                         (cor['chr2'] == str(chr2))]
            group = newcor.drop_duplicates(
                subset=['start1', 'end1', 'start2', 'end2'], keep='first', inplace=False)
            for index, row in group.iterrows():
                if (int(row['start1']) <= start1) and (int(row['end1']) >= end1) and (int(row['start2']) <= start2) and (int(row['end2']) >= end2):
                    homo = 0
                    for block in k[0]:
                        if (block[0] not in gff1.index) or (block[2] not in gff2.index):
                            continue
                        if block[0]+","+block[2] in homopairs.keys():
                            homo += homopairs[block[0]+","+block[2]]
                    homo = homo/len(k[0])
                    if homo <= float(row['homo1']) or homo >= float(row['homo2']):
                        continue
                    index = gff1[(gff1[0] == chr1) & (gff1[5] >= start1) & (
                        gff1[5] <= end1)].index
                    new_index = [i[0] for i in k[0]]
                    for i in range(1, int(self.wgd)+1):
                        name = 'L'+str(i)
                        old_index = gff1[gff1.index.isin(
                            index) & gff1[name].str.match(r'\w+') == True].index
                        inters = np.intersect1d(old_index, new_index)
                        if len(inters)/len(new_index) > 0.2:
                            continue
                        gff1.loc[gff1.index.isin(
                            index) & gff1[name].isnull(), name] = '.'
                        gff1.loc[new_index, name] = [i[2] for i in k[0]]
                        break
        return gff1