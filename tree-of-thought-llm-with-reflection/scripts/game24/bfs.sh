python ../../run.py \
    --backend gpt-3.5-turbo \
    --task game24 \
    --task_start_index 900 \
    --task_end_index 1000 \
    --method_generate propose \
    --method_evaluate value \
    --method_select greedy \
    --n_evaluate_sample 3 \
    --n_select_sample 5 \
    ${@}
