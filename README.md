# 项目名称
Crop_AL_Hub项目登录功能后端实现


## **使用流程**
1.查看是否下载flask-migrate : pip list

![Clip_2025-01-15_11-29-15](https://github.com/user-attachments/assets/f5b45e09-c6be-48b0-bb9d-78cbcec0a23c)

若无，则输入：pip install falsk-migrate

2.需要已有crop_all_hub数据库，删除migrations文件夹后依次运行

flask db init

flask db migrate

flask db upgrade

生成User表

3.往表里插入一条数据，表中的密码需存放加密后的密码，可先在表中输入密码“123123”后
用blueprint/utils/encryption.py将密码加密

4.按需修改.env中的配置

![Clip_2025-01-15_12-53-56](https://github.com/user-attachments/assets/1cab8a33-f2cf-42e1-8de2-1e471eb66a4a)

5.使用swagger或Postman进行测试时，需选择登录类型，如：

{

  "login_identifier": "12345678901",   // 假设使用手机号登录
  
  "login_type": "telephone",            // 可以是 "username", "telephone", "email"
  
  "password": "123123"
  
}
