# -*- coding: utf-8 -*-
"""
Created on Thu Mar 11 15:10:11 2021

@author: Michele
"""

import pandas as pd
import re
from datetime import datetime

vessels_info = pd.read_excel('vessels_info.xlsx')

relevant_columns = vessels_info[['Inst IMO No', 'Customer ID' , 'Customer Country', 'Main Engine Power (kW)', 'Inst Cluster', 'Inst BuiltDate', 'Product']]

d1 = datetime(2005, 1, 1).strftime("%d/%m/%Y") 

built_after_2005 = relevant_columns[relevant_columns['Inst BuiltDate'] > d1]

vessel_segments = ['Cruise Vessels', 'Passenger & Cargo Vessels', 'Passenger Vessels', 'RoRo Vessels', 'Gas Tankers',
'Container Vessels', 'Cargo Vessels', 'Bulk Carriers', 'Tankers', 'Fishing Vessels', 'Service Vessels', 'Inland Vessels',
'Offshore Support Vessels', 'Oil & Gas', 'Navy & Coast Guard Vessels']

#String Matching for "Inst Cluster" column with vessel segments types
df1 = built_after_2005[built_after_2005.apply(lambda x: x['Inst Cluster'] in vessel_segments, axis=1)]

df2 = pd.read_csv('vessels_design_speeds.csv', sep=";")

#Dataframe of design speeds matched with imo_list of df1
imo_list1 = df1['Inst IMO No'].values.tolist()
df3 = df2[df2.apply(lambda x: x['IMO'] in imo_list1 , axis = 1 )]

#Throw away wrong design speeds
df3['Design Speed (knots)'] = pd.to_numeric(df3['Design Speed (knots)'],errors='coerce')
df_design_speed = df3[df3['Design Speed (knots)'] < 100]

#Sync Df1 with erased rows
imo_list2 = df_design_speed['IMO'].values.tolist()
df_vessels_info = df1[df1.apply(lambda x: x['Inst IMO No'] in imo_list2 , axis = 1 )]

# # Px = (Sx/Sref)^3*Pref
#To use the function above i need the Max Operational Speed (MOS) first

df_3rd = pd.read_csv('vessels_speed_profile.csv', sep=";")

#filter data
vessels_speed_profile = df_3rd[df_3rd.apply(lambda x: x['imo'] in imo_list2 , axis = 1 )]
#This gives only 1403 rows so I will need to discard 42 imo datas from dataframe 1 and 2, since
#datframe 1 and 2 had 1445 rows

#Syncing df 1 and 2
imo_final_list = vessels_speed_profile['imo'].values.tolist()
df_vessels_info = df_vessels_info[df_vessels_info.apply(lambda x: x['Inst IMO No'] in imo_final_list , axis = 1 )]
df_design_speed = df_design_speed[df_design_speed.apply(lambda x: x['IMO'] in imo_final_list , axis = 1 )]

#Now I will calculate MOS
speed_greater_than_3 = vessels_speed_profile.drop(columns= ['imo', 'speed 0.0 - 0.5', 'speed 0.5 - 1.0', 'speed 1.0 - 1.5', 'speed 1.5 - 2.0', 'speed 2.0 - 2.5','speed 2.5 - 3.0'])

cumulative_sum = speed_greater_than_3.cumsum(axis=1)
normalized_df = cumulative_sum.iloc[:,:].div(cumulative_sum['speed >30.0'], axis=0)
filtered_df = normalized_df.where(normalized_df < 0.95) #This is for taking values that are under 0.95 cdf
mos_labels_values = filtered_df.idxmax(axis='columns', skipna=True)
mos_labels_values = mos_labels_values.str.findall(r'([0-9\.]+) - ([0-9\.]+)')
mos_labels_values.name = 'MOS'
df_imo_mos = pd.concat([vessels_speed_profile, mos_labels_values], axis=1)
df_imo_mos = df_imo_mos[['imo', 'MOS']].dropna()

def meanlist(lista):
    val1 = float(lista[0][0])
    val2 = float(lista[0][1])
    mean = (val1+val2)/2
    return mean


df_imo_mos['MOS'] = df_imo_mos['MOS'].apply(meanlist)
df_design_speed = df_design_speed.rename(columns={"Design Speed (knots)" : "Design speed"})
df_vessels_info = df_vessels_info.rename(columns={"Inst IMO No": "IMO"})
df_imo_mos = df_imo_mos.rename(columns={"imo": "IMO"})

df_vessels_info = pd.merge(df_vessels_info, df_imo_mos, on= 'IMO')
df_vessels_info = pd.merge(df_vessels_info, df_design_speed, on= 'IMO')
#Filter those Vessels already working below the design speed
df_vessels_info = df_vessels_info[df_vessels_info['MOS'] < df_vessels_info['Design speed']]

df_vessels_info['Real Prop Power Demand']= df_vessels_info.apply(lambda x: (x['MOS']/x['Design speed'])**3*x['Main Engine Power (kW)']*0.85, axis=1)

#I think that the Installed Propulsion Power is equal to the Main Engine Power
df_vessels_info['EPL'] = df_vessels_info.apply(lambda x: x['Main Engine Power (kW)'] - x['Real Prop Power Demand']/0.85  , axis=1)
df_vessels_info['Design speed - MOS'] = df_vessels_info.apply(lambda x: x['Design speed'] - x['MOS']  , axis=1)
df_vessels_info = df_vessels_info.sort_values(by='EPL', ascending=False)

#Uncomment to export vessels_info dataframe with MOS, Design speed and EPL to excel format
df_vessels_info.to_excel('EPL adressable.xlsx')
