import os
import boto3
from tqdm import tqdm

class AWSManager(object):
    """
    class to manage aws operations securely.

    methods:
        upload_file: To upload file to AWS.
        get_download_link: To get download link.
        list_aws_dir: To list files in AWS directory.

    """
    __aws_client = None
    bucket_name = ''

    class ProgressPercentage(object):
        """
        class for uploading progress bar.
        """
        def __init__(self, file_path, progress_bar):
            self._file_path = file_path
            self._progress_bar = progress_bar
            self._uploaded_bytes = 0

        def __call__(self, bytes_amount):
            self._uploaded_bytes += bytes_amount
            self._progress_bar.update(bytes_amount)
    

    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name, bucket_name):
        self.bucket_name = bucket_name

        self.__aws_client = boto3.client(
                                            's3',
                                            aws_access_key_id= aws_access_key_id,
                                            aws_secret_access_key= aws_secret_access_key,
                                            region_name= region_name
                                        )
    
    def upload_file(self, file_path: str, s3_file_path:str) -> bool:
        """
        Uploads the defined file to the specified s3_file_path.

        Args:
            file_path (str): file path of the file which is to be uploaded.
            s3_file_path (str): s3 directory path where the file to be uploaded.

        Returns:
            (bool) : If operation is successful returns True.
                     If operation is unsuccessful returns False.
        """
        try:
            with tqdm(total=os.path.getsize(file_path), unit='B', unit_scale=True, desc='Uploading') as progress_bar:
                self.__aws_client.upload_file(file_path, self.bucket_name, s3_file_path, Callback= self.ProgressPercentage(file_path, progress_bar))

            return True
        
        except Exception as e:
            raise
            return False


    def get_download_link(self, s3_file_path: str, link_expire_time:int=None) -> tuple[bool, str]:
        """
        Generates the download link of defined s3_file_path.

        Args:
            s3_file_path (str): s3 file location.
            link_expire_time (int, optional): in how much time download link will be expired. defaults to None

        Returns:
            (tuple) : returns the tuple which has (bool, str)
                      if operation is successful : returns True and the download link.
                      if operation is unsuccessful : returns False and empty string.
        """


        if isinstance(link_expire_time, int):
            try:
                download_link = self.__aws_client.generate_presigned_url(
                                                                            ClientMethod='get_object',
                                                                            Params={'Bucket': self.bucket_name, 'Key': s3_file_path},
                                                                            ExpiresIn=link_expire_time
                                                                        )
                return True, download_link
            except Exception as e:
                print(e)
                return False, ''
        
        else:
            download_link = f"https://{self.bucket_name}.s3.ap-south-1.amazonaws.com/{s3_file_path}"
            return True, download_link
    


    def list_aws_dir(self, s3_folder_path: str) -> tuple[bool, list]:
        """
        list all the files inside defined s3_folder_path

        Args:
            folder_path (str): path of the directory inside bucket end with forward slash '/'.
                                (e.g.) "directory/path/"

        Returns:
            (tuple): returns the tuple which has (bool, list)
                     if bool is True then operation is successful or not.
                     in case of False, list will be empty.
        """

        try:
            response = self.__aws_client.list_objects_v2(Bucket=self.bucket_name, Prefix=s3_folder_path)

            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                return True, files
            else:
                return True, []
        except Exception as e:
            return False, []