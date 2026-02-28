#!/bin/bash


while getopts c:w:j:f:h option
do 
    case "${option}"
        in
        # c)conda_env=${OPTARG};;
        c)v_env=${OPTARG};;
        w)work_dir=${OPTARG};;
        j)kwargs_json=${OPTARG};;
        f)python_file=${OPTARG};;
        h)echo -e "Bash script to activate  \nUsage:\n\t-c \t Anaconda env name.\n\t-w \t Work Directory.\n\t-j \t Payload Json file.\n\t-h \t Help."
            exit;;
    esac
done



echo -e "\n********************************************************************"
echo "inside main.sh ( $$ ) got the arguments"
echo "work_dir : $work_dir "
echo "kwargs_json : $kwargs_json "
echo -e "********************************************************************\n"

# echo "activating conda environment : $conda_env"
# source activate $conda_env

echo "activating virtual environment : $v_env"
source $v_env


echo "changing directory : $work_dir"
cd $work_dir


echo "starting python script"
python $python_file -f $kwargs_json

# echo "press any key to exit .... "
# read exit_signal


echo "exiting the main.sh"
