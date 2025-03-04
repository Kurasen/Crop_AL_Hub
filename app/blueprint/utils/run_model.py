import subprocess
import logging

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 配置远程服务器信息
CONNE = {
    'host':'10.0.4.71',
    'user':'chenwanyue',
    'rsa':'/Users/chenwanyue/.ssh/rsa100471',
    'info':'chenwanyue@10.0.4.71',
    'workspace':'/home/chenwanyue/workspace/'
}

# 远程运行程序
def run_command_remote(command):
    try:
        ssh_command = f"ssh -i {CONNE['rsa']} {CONNE['info']} {command}"
        result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True, check=True)
        logging.info(result.stdout)
    except FileNotFoundError as e:
        logging.error(f"错误: SSH 密钥文件未找到 - {e}")
    except subprocess.CalledProcessError as e:
        logging.error(f"执行 SSH 命令时出错，返回码: {e.returncode},标准错误: {e.stderr}")
    except Exception as e:
        logging.error(f"发生未知错误: {e}")

# 在本地运行程序
def run_command_local(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        logging.info(result)
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败，错误信息：{e.stderr}")
        logging.error(f"命令执行失败，错误信息：{e.stderr}")

def clean_file(run_func, files):
    clean_cmd = f"sudo rm -r {files}"
    logging.debug(clean_cmd)
    run_func(clean_cmd)

# 获取模型运行的文件输出        
def get_output(result_dir, output_file):
    cat_cmd = f"cat {result_dir}/{output_file}"
    ssh_command = f"ssh -i {CONNE['rsa']} {CONNE['info']} {cat_cmd}"
    result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True, check=True)
    return result.stdout

# 上传数据集到远程服务器
def upload_database_remote(remote_path,local_path):    
    mkdir_cmd =f"mkdir -p {remote_path}"
    run_command_remote(mkdir_cmd)

    #上传文件
    scp_command = f"scp -i {CONNE['rsa']} -r {local_path} {CONNE['info']}:{remote_path}"
    result = subprocess.run(scp_command, shell=True, capture_output=True, text=True)
    print(result)

# 从远程服务器下载一张图片
def download_img_remote(remote_file_path,local_path):
    scp_command = f"scp -i {CONNE['rsa']} {CONNE['info']}:{remote_file_path} {local_path}"
    result = subprocess.run(scp_command, shell=True, capture_output=True, text=True)
    print(result)

# 上传一张图到远程服务器
def upload_img_remote(remote_path,file_path):    
    mkdir_cmd =f"mkdir -p {remote_path}"
    run_command_remote(mkdir_cmd)

    #上传文件
    scp_command = f"scp -i {CONNE['rsa']} {file_path} {CONNE['info']}:{remote_path}"
    result = subprocess.run(scp_command, shell=True, capture_output=True, text=True)
    print(result)

# 模拟的图像处理函数
def run_models_in_container(run_func, data_path, model_image, instruction):
    only_tag = f"User1_{model_image}"

    #创建输出文件夹
    result_dir = f"{data_path}/{only_tag}"
    mkdir_cmd =f"mkdir -p {result_dir}"
    logging.debug(mkdir_cmd)
    run_func(mkdir_cmd)

    #运行容器
    docker_cmd = f"sudo docker run --name {only_tag}\
        --mount type=bind,source={result_dir},target=/result\
        --mount type=bind,source={data_path},target=/data\
        {model_image} python3 main.py -i /data -o /result {instruction}"
    logging.debug(docker_cmd)
    run_func(docker_cmd)
    
    #清理环境
    clean_cmd = f"sudo docker rm -f {only_tag}"
    logging.debug(clean_cmd)
    run_func(clean_cmd)
    
    return result_dir

# 在数据集上运行模型
def run_dataset_on_models_in_container(run_func, dataset_path, model_image, container_name, instruction, output_file):
    dataset_dir = CONNE['workspace'] + dataset_path
    result_dir = f"{dataset_dir}/{container_name}/result"
    
    #创建输出文件夹
    mkdir_cmd =f"mkdir -p {result_dir}"
    logging.debug(mkdir_cmd)
    run_func(mkdir_cmd)

    #运行容器
    docker_cmd = f"sudo docker run --name {container_name}\
        --mount type=bind,source={result_dir},target=/result\
        --mount type=bind,source={dataset_dir},target=/data\
        {model_image} python3 main.py -i /data -o /result {instruction}"
    logging.debug(docker_cmd)
    run_func(docker_cmd)
    
    #获取执行结果
    output = get_output(result_dir,output_file)

    #清理环境
    clean_cmd = f"sudo docker rm -f {container_name}"
    logging.debug(clean_cmd)
    run_func(clean_cmd)
    clean_cmd = f"sudo rm -r {dataset_dir}/{container_name}"
    logging.debug(clean_cmd)
    run_func(clean_cmd)
    return output

if __name__ == "__main__":
    #output = run_dataset_on_models_in_container(run_command_remote,"detetcion-tassel/dataset/test","detetcion-tassel","mytestCary","", "detection_results.txt")
    #output = run_dataset_on_models_in_container(run_command_remote,"segmentation-tassel/dataset/test","segmentation-tassel","mytestCary","", "segmentation_results.txt")
    #output = run_dataset_on_models_in_container(run_command_remote,"detetcion-seed-leaf/dataset/test/ng","detetcion-seed-leaf","mytestCary","-m ngp", "plant_detection_summary.csv")
    #output = run_dataset_on_models_in_container(run_command_remote,"detetcion-seed-leaf/dataset/test/uav","detetcion-seed-leaf","mytestCary","-m uavp", "plant_detection_summary.csv")
    #output = run_dataset_on_models_in_container(run_command_remote,"detetcion-seed-leaf/dataset/test/ng","detetcion-seed-leaf","mytestCary","-m ngl", "leaf_detection_summary.csv")
    #output = run_dataset_on_models_in_container(run_command_remote,"detetcion-seed-leaf/dataset/test/uav","detetcion-seed-leaf","mytestCary","-m uavl", "leaf_detection_summary.csv")


    result_dir = run_models_in_container(run_command_remote, CONNE['workspace']+"segmentation-tassel/dataset/test", "segmentation-tassel", "")
    output = get_output(result_dir, "segmentation_results.txt")
    print(output)
    clean_file(run_command_remote, result_dir)
    pass
