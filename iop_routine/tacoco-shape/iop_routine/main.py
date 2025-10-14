# coding=utf-8
import datetime
import matplotlib.pyplot as plt
import re
import pandas as pd
import numpy as np
import random
import shap
import os
from xgboost import XGBClassifier
from DataWrapper import DataWrapper
from functools import partial
import iop_features
import json

def gen_date_json(today_date="2022-06-11"):
    

    features_order = [
        'CWVatDongsha','CWVatNETW', 'WSatBanqiao', 'WSatNETW', 'CrossStraitUatNWTW', 'UatNETW',
        'swUatDongSha', 'swUatDongShaNaN', 'sUatNETW', 'sUatNETWNaN',
        'swDEPTHatNETW', 'MSEatNETW', 'swLAYERatSWTW', 'IVTatDongSha',
        'IVTatDongShaNaN', 'LeeVortex', 'CAPEatNETW', 'CRHatNETW',
        'deltaCWVatTW', 'deltaLTSatSWTW', 'zetaatETW', 'seUatETW',
        'month',
        #'year','month','day'
    ]

    features_render = {
        'CWVatDongsha'          : {'name' : 'CWV_Dongsha'                            , 'unit': 'mm'        , "coeff": 1.0    },
        'CWVatNETW'             : {'name' : 'CWV_NETW'                               , 'unit': 'mm'        , "coeff": 1.0    },
        'WSatBanqiao'           : {'name' : 'WindShear_Banqiao'                      , 'unit': 'm/s'       , "coeff": 1.0    },
        'WSatNETW'              : {'name' : 'WindShear_NETW'                         , 'unit': 'm/s'       , "coeff": 1.0    },
        'CrossStraitUatNWTW'    : {'name' : 'CrossTaiwanStraitWindSpeed_NWTW'        , 'unit': 'm/s'       , "coeff": 1.0    },
        'UatNETW'               : {'name' : 'WindSpeed_NETW'                         , 'unit': 'm/s'       , "coeff": 1.0    },
        'swUatDongSha'          : {'name' : 'SouthwesterlyWindSpeed_DongSha'         , 'unit': 'm/s'       , "coeff": 1.0    },
        'swUatDongShaNaN'       : {'name' : 'SouthwesterlyWindSpeed_DongSha_NaN'     , 'unit': 'Y/N'       , "coeff": 1.0    },
        'sUatNETW'              : {'name' : 'SoutherlyWindSpeed_NETW'                , 'unit': 'm/s'       , "coeff": 1.0    }, 
        'sUatNETWNaN'           : {'name' : 'SoutherlyWindSpeed_NETW_NaN'            , 'unit': 'Y/N'       , "coeff": 1.0    },
        'swDEPTHatNETW'         : {'name' : 'SouthwesterlyDepth_NETW'                , 'unit': 'non dim.'  , "coeff": 1.0    },
        'MSEatNETW'             : {'name' : 'MSE_NETW'                               , 'unit': 'K'         , "coeff": 1/1004 },
        'swLAYERatSWTW'         : {'name' : 'SouthwesterlyLayer_SWTW'                , 'unit': 'non dim.'  , "coeff": 1.0    },
        'IVTatDongSha'          : {'name' : 'IVT_Dongsha'                            , 'unit': 'kg/m/s'    , "coeff": 1.0    },
        'IVTatDongShaNaN'       : {'name' : 'IVT_Dongsha_NaN'                        , 'unit': 'Y/N'       , "coeff": 1.0    },
        'LeeVortex'             : {'name' : 'LeeVortex'                              , 'unit': '1E-5 1/s'  , "coeff": 1E5    },
        'CAPEatNETW'            : {'name' : 'CAPE_NETW'                              , 'unit': 'J/kg'      , "coeff": 1.0    },
        'CRHatNETW'             : {'name' : 'CRH_NETW'                               , 'unit': 'non dim.'  , "coeff": 1.0    },
        'deltaCWVatTW'          : {'name' : 'CWVanomaly_TW'                          , 'unit': 'mm'        , "coeff": 1.0    },
        'deltaLTSatSWTW'        : {'name' : 'LTSanomaly_SWTW'                        , 'unit': 'K'         , "coeff": 1.0    },
        'zetaatETW'             : {'name' : 'zeta_ETW'                               , 'unit': 'Y/N'       , "coeff": 1.0    },
        'seUatETW'              : {'name' : 'SoutheasterlyWindSpeed_ETW'             , 'unit': 'non dim.'  , "coeff": 1.0    },
        'month'                 : {'name' : 'Month'                                  , 'unit': 'month'     , "coeff": 1.0    },
    }
    features_order_id=[
        'D10-01','B07-16','D10-03','R09-19','R10-07-1','R10-07-2',
        'R10-01','R10-01-nan','R10-08','R10-08-nan',
        'R09-01','R10-10','D08-02','R10-19,B08-14',
        'R10-19,B08-14-nan','R10-07','B07-39','R08-07',
        'B07-10','R10-29','R09-12-1','R09-12-2',
        "month"
    ]

#features_max_min = {
#    "CWVatDongsha" : { "max" : 78.85395226 , "min" : 16.6865975 },
#}

    features_max_min = {}

    df = pd.read_csv('features_nan_sep_weak_afternoon_date.csv')
    df_max = df.max(axis=0)
    df_min = df.min(axis=0)


    for idx, row in df_max.iteritems():
        if idx not in features_max_min.keys():
            features_max_min[idx] = {}
        features_max_min[idx]["max"] = row
    for idx, row in df_min.iteritems():
        features_max_min[idx]["min"] = row

#print(features_max_min)


    wrapper = DataWrapper('/data/flyingmars/iop_files/pickle',data_type="gfs")

    for f_day in range(0,6):

        data_wrapper = partial(wrapper.get_data,forecast_day=f_day,date=today_date)

#print(data_wrapper(time=1,lev=2,var="T"))


        X = list()
        feature_ori_val = dict()
        for feature in features_order :
            cal_func_name = feature
            nan_feature = False
            searched = re.search(r"(.+)NaN$",feature)
            if searched :
                cal_func_name =  searched[1]
                nan_feature = True

            ret_val = 0.0
            if feature == "month" :
                # month
                month_int = int(today_date[5:7])
                ret_val = (month_int - 5) / (10 - 5)
                feature_ori_val[feature] = "{:02d}".format(month_int)
            elif nan_feature:
                # nan case
                func_ret = iop_features.__dict__["cal_" + cal_func_name](data_wrapper)
                if func_ret < -9998 :
                    ret_val = 1.0
                    feature_ori_val[feature] = "Y"
                else:
                    ret_val = 0.0
                    feature_ori_val[feature] = "N"
            else:
                # normal case
                func_ret = iop_features.__dict__["cal_" + cal_func_name](data_wrapper)
                if func_ret < -9998 :
                    func_ret = 0.0  # nan 
                max_val = features_max_min[cal_func_name]["max"]
                min_val = features_max_min[cal_func_name]["min"]
                ret_val = (func_ret - min_val) / (max_val - min_val)
                feature_ori_val[feature] = "{:10.2f}".format(func_ret * features_render[feature]["coeff"])
                if features_render[feature]["unit"] == "Y/N" :
                    if func_ret > 0.5 :
                        feature_ori_val[feature] = "Y"
                    else:
                        feature_ori_val[feature] = "N"
            
            print(feature,func_ret,ret_val)
            X.append(ret_val)

        #print(X)
        #print(len(X))    


        xgboostModel = XGBClassifier(
            use_label_encoder=False
        )
        xgboostModel.load_model("best_model.json")
        predicted = xgboostModel.predict_proba([X])

        explainer = shap.TreeExplainer(xgboostModel)
        shap_values = explainer.shap_values(np.array([X]))

        out_json = dict()
        out_json["content"] = list()
        out_json["fig"] = list()

        #plt.figure(1,figsize=(16, 14),dpi=300)
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values[0],
                base_values=explainer.expected_value,
                data=np.array(X),
                feature_names=features_order
            ),
            max_display=15,
            show=False
        )
        plt.gcf().set_size_inches(12, 6)
        plt.tight_layout()
        #fig = plt.gcf()
        #fig.set_figheight(30)
        #fig.set_figwidth(14)
        #ax = plt.gca()
        #ax.set_yticklabels(ax.get_yticklabels(),fontsize=30)
        #plt.rcParams.update({'font.size': 30})
        #fig.set_size_inches(16,12)
        #plt.rcParams.update({'figure.figsize':  (25, 14)})
        #plt.show()
        plt.savefig("/data/flyingmars/iop_files/graph/"+today_date+"_"+str(f_day*24)+".jpg",dpi=300)
        plt.savefig("/data/TACOCO2025/graphs/SHAP_analysis/"+today_date+"_{:03d}".format(f_day*24)+".jpg",dpi=300)
        
        out_json["content"].append(
            { "name" : "Prob. of Rainfall Label" , "value" : "{:10.3f}".format(predicted[0][1]*100) , "unit" : "%" } 
        )
        for feature in features_order :
            out_json["content"].append(
                { 
                    "name"  : features_render[feature]["name"],
                    "value" : feature_ori_val[feature],
                    "unit"  : features_render[feature]["unit"] 
                } 
            )
        out_json["fig"].append(
            "/data/flyingmars/iop_files/graph/"+today_date+"_"+str(f_day*24)+".jpg"
        )

        with open("/data/flyingmars/iop_files/json/"+ today_date +"_"+str(f_day*24)+".json","w",encoding="utf8") as fp:
            json.dump(out_json,fp)
        
        if f_day == 2 :
            with open("/data/flyingmars/iop_files/json/"+ today_date +".json","w",encoding="utf8") as fp:
                json.dump(out_json,fp)
        plt.close()
        #print(predicted)
        #print(shap_values)


if __name__ == "__main__":

    now = datetime.datetime.now()
    # now = now - datetime.timedelta(days=1)
    print("now=",now)
    now_str = now.strftime("%Y-%m-%d")
    print("now_str=",now_str)
    gen_date_json(now_str)
    #gen_date_json("2022-08-27")



