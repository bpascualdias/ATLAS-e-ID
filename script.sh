dir=/lcg/storage19/atlas/godin/el_classifier #/home/dgodin/el_classifier
export SCRIPT_VAR
for SCRIPT_VAR in 1 2 3 4 5
do
    sbatch --array=1-10 ${dir}/sbatch.sh $SCRIPT_VAR
done
