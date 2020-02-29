import os
import numpy as np
import settings
import pickle
import settings

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.ensemble import RandomForestRegressor
import multiprocessing

def get_int_runs(patient_idx):
    """

    :param patient_idx:
    :return: list with all run files for the given patient
    """
    os.listdir(settings.out_path_folder_downsampled)
    if patient_idx < 10:
        subject_id = str('00') + str(patient_idx)
    else:
        subject_id = str('0') + str(patient_idx)
    list_subject = [i for i in os.listdir(settings.out_path_folder_downsampled) if i.startswith('sub-'+subject_id) and i.endswith('.p')]
    return list_subject


def get_act_int_list(patient_idx):
    """

    :param patient_idx:
    :return: array in shape (runs_for_patient_idx, 94) including the active grid points in every run
    """

    runs_ = get_int_runs(patient_idx)
    act_ = np.zeros([len(runs_), 94])
    for idx in range(len(runs_)):
        file = open(settings.out_path_folder + '/' + runs_[idx], 'rb')
        out = pickle.load(file)

        act_[idx, :] = out['act_grid_points']

    return act_

def save_all_act_grid_points():
    """
    function that saves all active grid points in a numpy file --> concatenated as a list over all patients
    can be loaded with act_ = np.load('act_.npy')
    :return:
    """
    l_act = []
    for patient_idx in range(16):
        l_act.append(get_act_int_list(patient_idx))
    np.save('act_.npy', np.array(l_act))


def get_train_test_dat(patient_test, grid_point, act_, Train=True):
    """
    For a given grid_point, and a given provided test patient, acquire all combined dat and label information
    :param patient_test:
    :param grid_point:
    :param act_:
    :param Train: determine if data is returned only from patient_test, or from all other
    :return: concatenated dat, label
    """
    start = 0
    for patient_idx in range(16):
        if Train is True and patient_idx == patient_test:
            continue
        if Train is False and patient_idx != patient_test:
            continue
        # now load from every patient that has data for that grid point
        if grid_point in np.nonzero(np.sum(act_[patient_idx], axis=0))[0]:
            runs = get_int_runs(patient_idx)
            for run_idx, run in enumerate(runs):
                # does this run has the grid point?
                if act_[patient_idx][run_idx, grid_point] != 0:
                    # load file
                    file = open(settings.out_path_folder_downsampled + '/' + run, 'rb')
                    out = pickle.load(file)

                    # fill dat
                    if start == 0:
                        dat = out['int_data'][grid_point]
                        if grid_point < 39 or (grid_point > 78 and grid_point < 86):  # contralateral
                            label = out['label_mov'][0, :]
                        else:
                            label = out['label_mov'][1, :]
                        start = 1
                    else:
                        dat = np.concatenate((dat, out['int_data'][grid_point]), axis=1)

                        if grid_point < 39 or (grid_point > 78 and grid_point < 86):  # contralateral
                            label = np.concatenate((label, out['label_mov'][0, :]), axis=0)
                        else:
                            label = np.concatenate((label, out['label_mov'][1, :]), axis=0)
    return dat, label

def run_CV(patient_test, model_fun = RandomForestRegressor):
    """
    given model is trained grid point wise for the provided patient
    saves output estimations and labels in a struct with r2 correlation coefficient
    :param patient_test: CV patient to test
    :param model_fun: provided model function
    :return:
    """
    act_ = np.load('act_.npy')  # load array with active grid points for all patients and runs

    #get all active grid_points for that patient
    arr_active_grid_points = np.zeros(94)
    arr_active_grid_points[np.nonzero(np.sum(act_[patient_test], axis=0))[0]] = 1

    patient_CV_out = np.empty(94, dtype=object)

    for grid_point in np.nonzero(arr_active_grid_points)[0]:

        dat, label = get_train_test_dat(patient_test, grid_point, act_, Train=True)

        dat_test, label_test = get_train_test_dat(patient_test, grid_point, act_, Train=False)

        model = model_fun(n_estimators=32, max_depth=4)
        model.fit(dat.T, label)

        y_pred = model.predict(dat_test.T)

        predict_ = {
            "prediction": y_pred,
            "out_cc": r2_score(label_test, y_pred),
            "true_label": label_test
        }

        patient_CV_out[grid_point] = predict_

    if patient_test < 10:
        subject_id = str('00') + str(patient_test)
    else:
        subject_id = str('0') + str(patient_test)

    out_path_file = os.path.join(settings.out_path_folder_downsampled, subject_id+'prediction.npy')
    np.save(out_path_file, patient_CV_out)

if __name__== "__main__":

    pool = multiprocessing.Pool()
    pool.map(run_CV, np.arange(16))