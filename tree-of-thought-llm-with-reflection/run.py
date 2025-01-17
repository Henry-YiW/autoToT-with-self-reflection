import os
import json
import argparse

from tot.tasks import get_task
from tot.methods.bfs import solve_with_reflection, solve_without_reflection, naive_solve
from tot.models import gpt_usage

def run(args):
    task = get_task(args.task)
    logs, cnt_avg, cnt_any = [], 0, 0
    
    # File paths
    reflection_types = []
    if args.enable_local_reflection:
        reflection_types.append("local")
    if args.enable_global_reflection:
        reflection_types.append("global")
    reflection_suffix = f"_{'-'.join(reflection_types)}" if reflection_types else ""

    if args.naive_run:
        log_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_naive_{args.prompt_sample}_sample_{args.n_generate_sample}_start{args.task_start_index}_end{args.task_end_index}.json'
    else:
        log_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_{args.method_generate}{args.n_generate_sample}_{args.method_evaluate}{args.n_evaluate_sample}_{args.method_select}{args.n_select_sample}{reflection_suffix}_start{args.task_start_index}_end{args.task_end_index}.json'
    
    # Only create reflection_file path if global reflection is enabled
    reflection_file = None
    if args.enable_global_reflection:
        reflection_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_global_reflection_{args.method_generate}{args.n_generate_sample}_start{args.task_start_index}_end{args.task_end_index}.json'

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Initialize global reflection memory only if global reflection is enabled
    global_reflection_memory = []
    if args.enable_global_reflection and reflection_file and os.path.isfile(reflection_file):
        with open(reflection_file, 'r') as rf:
            try:
                existing_data = json.load(rf)
                if 'global_reflection_memory' in existing_data:
                    global_reflection_memory = existing_data['global_reflection_memory']
            except json.JSONDecodeError:
                pass
    
    print("FUCK GLOBAL REFLECTION MEMORY", global_reflection_memory)
    for i in range(args.task_start_index, args.task_end_index):
        # Choose solving method
        if args.naive_run:
            ys, info = naive_solve(args, task, i)
        elif args.enable_local_reflection or args.enable_global_reflection:
            ys, info = solve_with_reflection(args, task, i, global_reflection_memory)
        else:
            ys, info = solve_without_reflection(args, task, i)

        # Update global reflection memory from the latest solve
        if args.enable_global_reflection and "steps" in info:
            for step_info in info["steps"]:
                if "global_reflections" in step_info:
                    for reflection in step_info["global_reflections"]:
                        if reflection not in global_reflection_memory:
                            global_reflection_memory.append(reflection)

        # log task info
        infos = [task.test_output(i, y) for y in ys]
        info.update({
            'idx': i, 
            'ys': ys, 
            'infos': infos, 
            'usage_so_far': gpt_usage(args.backend),
            'global_reflection_memory': global_reflection_memory if args.enable_global_reflection else []
        })
        logs.append(info)
        
        # Write to log file incrementally
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=4)

        # Update metrics
        accs = [inf['r'] for inf in infos]
        cnt_avg += sum(accs) / len(accs)
        cnt_any += any(accs)
        print(i, 'sum(accs)', sum(accs), 'cnt_avg', cnt_avg, 'cnt_any', cnt_any, '\n')
    
    # After the loop ends, write the global reflection memory if enabled
    if args.enable_global_reflection and reflection_file:
        with open(reflection_file, 'w') as rf:
            json.dump({
                'global_reflection_memory': global_reflection_memory,
                'last_index': args.task_end_index - 1
            }, rf, indent=4)

    n = args.task_end_index - args.task_start_index
    print(cnt_avg / n, cnt_any / n)
    print('usage_so_far', gpt_usage(args.backend))

def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('--backend', type=str, choices=['gpt-4', 'gpt-3.5-turbo'], default='gpt-4')
    args.add_argument('--temperature', type=float, default=0.7)

    args.add_argument('--task', type=str, required=True, choices=['game24', 'text', 'crosswords'])
    args.add_argument('--task_start_index', type=int, default=900)
    args.add_argument('--task_end_index', type=int, default=1000)

    args.add_argument('--naive_run', action='store_true')
    args.add_argument('--prompt_sample', type=str, choices=['standard', 'cot'])  # only used when method_generate = sample, or naive_run

    args.add_argument('--method_generate', type=str, choices=['sample', 'propose'])
    args.add_argument('--method_evaluate', type=str, choices=['value', 'vote'])
    args.add_argument('--method_select', type=str, choices=['sample', 'greedy'], default='greedy')
    args.add_argument('--n_generate_sample', type=int, default=1)  # only thing needed if naive_run
    args.add_argument('--n_evaluate_sample', type=int, default=1)
    args.add_argument('--n_select_sample', type=int, default=1)
    
    # Reflection-related arguments
    args.add_argument('--enable_local_reflection', action='store_true',
                     help='Enable local reflection within each run')
    args.add_argument('--enable_global_reflection', action='store_true',
                     help='Enable global reflection across all runs')
    args.add_argument('--threshold', type=float, default=0.5,
                     help='Threshold value for triggering reflections')

    args = args.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    print(args)
    run(args)
