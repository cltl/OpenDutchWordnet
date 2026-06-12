#check if enough arguments are passed, else print usage information
if [ $# -eq 0 ];
then
    echo
    echo "This script is meant to help check if the correct versions of python and virtualenv are installed."
    echo "It will perform checks for this and will try to install external python modules with pip."
    echo "If there is any error in one of these steps, the script will exit."
    echo
    echo "Usage                     : $0 python_version wanted_virtual_env_version vir_env_dir ext_modules"
    echo
    echo "python_version            : python version (major.minor for example 3.4)"
    echo "vir_env_dir               : full path (not just name of folder) to virtual environment directory (will be created)"
    echo "ext_modules               : path to file in which each line contains a module_name (pip install module_name is run)"
    exit -1
fi

#rename user input to logical variable names
cwd=${PWD#*}
log=$cwd/log
rm -rf $log && mkdir $log

python_version=$1
vir_env_dir=$2
ext_modules=$3

function command_check () {

RETVAL=$?
[ $RETVAL -eq 0 ] && echo $succes
[ $RETVAL -ne 0 ] && echo $failure && echo 'exiting...' && exit -1

}
#check if python version is installed
echo
echo "Checking python version"
export succes="Succes: python$python_version is installed"
export failure="Fail: please install python version $python_version"

python$python_version -c "exit()"
command_check

#create virtualenv and echo source command to stdout
echo 
echo "Creating virtual environment"
virtualenv --python=python$python_version --system-site-packages $vir_env_dir
echo
echo "to activate: source $vir_env_dir/bin/activate"
echo 
echo "activating virtualenv"
source $vir_env_dir/bin/activate

#install external python modules
echo
echo "Installing external python modules"

while read p
do
    export succes="Succes: succesfully installed module $p"
    export failure="Failure: error in installing module $p, please inspect $log/$p.log or $log/$p.log for the error log"
    pip install $p > $log/$p.log 2> $log/$p.err
    command_check

done < $ext_modules
echo
echo "#############################################################"
echo "it seems that the virtual environment was succesfully created"
echo
echo "virtual environment directory can be found here:" 
echo "$vir_env_dir"
echo
echo "to activate run:"
echo "source $vir_env_dir/bin/activate"
echo "to not have to do this everything, add the above command to files like ~/.bash_profile (files that are run on login)"
