import os
import time


def search_file(name, path_list):
    result = []
    if len(path_list) == 0:
        path_list = ["D:\\beijing_files\\beijing_files"]
    for path in path_list:
        for root, folder, files in os.walk(path):
            for file_name in files:
                if name in file_name:
                    file_path = os.path.abspath(os.path.join(root, file_name))

                    stat_info = os.stat(file_path)

                    # 时间戳转换
                    create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat_info.st_ctime))
                    modif_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat_info.st_mtime))

                    result.append([file_name, file_path, create_time, modif_time])  # 保存路径与盘符
    return result
