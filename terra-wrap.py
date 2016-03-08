#!/usr/bin/python 

progvers = "%prog 0.1"

from optparse import OptionParser
import sys
import os
import subprocess
import re


class terraform_this():
    def __init__(self):
        self.collect_opts()
        self.init_default_opts()

    def init_default_opts(self):

        if 'TERRAWRAP_PATH' not in os.environ:
            path=os.getcwd()
        else:
            path=os.environ['TERRAWRAP_PATH']
        
        if 'TERRAWRAP_PROG' not in os.environ:
            print os.environ
            if os.path.exists('/usr/bin/terraform'):
                prog='/usr/bin/terraform'
            else:
                exit('TERRAWRAP_PROG env var not defined , this should be full path to your terraform binary')
        else:
            if os.path.exists(os.environ.get('TERRAWRAP_PROG')):
                prog=os.environ.get('TERRAWRAP_PROG')
            else:
                exit('could not find TERRAWRAP_PROG binnary ,please define TERRAWRAP_PROG env var , this should be full path to your terraform binary')
        
        default_opts = {
                    'prog': prog,
                    'path': path,
                }
        self.path=default_opts['path']
        self.prog=default_opts['prog']
        
        if not 'S3_REGION' in os.environ or not 'S3_BUCKET' in os.environ:
            exit('S3_REGION or S3_BUCKET one or both ENV vars are not defined')
        
        self.default_opts = default_opts 

    def collect_opts(self):
            epilog="""ENV_VARS: AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY,S3_REGION,S3_BUCKET,TERRAWRAP_PROG"""
            parser = OptionParser(version=progvers,usage='usage: %prog [-q][-k] [plan|apply]',epilog=epilog)
            parser.description='This is a terraform wrapper targeted, this will make sure you are always using S3 backned for state files'
            parser.add_option("-k", "--key", dest = "key" , default='', help="specify S3 key where to store tfstate files")
            parser.add_option("-q", "--quiet", dest='quiet' , action='store_true', default = False, help="try to be quiet")
            (options, args) = parser.parse_args()
            self.options = options
            return options

    def get_git_dir(self):
        data = subprocess.Popen(['git','remote','show','-n','origin'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data.wait()
        if data.returncode == 0:
            out, err = data.communicate()
            for line in out.splitlines():
                if 'Fetch' in line:
                    match = re.search('\/.*',line)
                    if match != None:
                        self.key =  match.group(0).split('.')[0].replace('/','')
                    else:
                        exit('can not figure out the repo name base on your origin, please use  -k key to specify the key')
        else:
            exit('your git does not seem to have a remote origin set please set or use -k key to specify the key')

        #let's find out the relative path to the .git base this will be used to compound the S3_KEY
        data = subprocess.Popen(['git','rev-parse','--show-toplevel'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data.wait()
        if data.returncode == 0:
            self.top_level_path, err = data.communicate()
            self.top_level_path =  self.top_level_path.rstrip()
        else:
            exit('can not determine the relative path, please issue a BUG to vmindru')

        #print "self.key: {} , self.top_level_path: {}, self.path: {}".format(self.key, self.top_level_path, self.path)
        # CONVERT STRING TO ARRAY AND SUBSTRACT THE RELATIVE PATH 
        s0 = self.path.split('/')
        s1 = self.top_level_path.split('/')
        for item in s1:
            s0.remove(item)
        self.relative_path =  "/".join(s0)
        return self.key

    def build_configure_args(self):
        if self.options.key == '':
            self.get_git_dir()
            if self.key == False:
                if 'S3_KEY' in os.environ and self.options.quiet == False:
                    answer = 'UNDEF'
                    while answer not in ['Yes','yes','No','no','Y','y','N','n','']:
                        sys.stdout.write("S3_KEY seems to  be set to: \"%s\" , use this value? Y/N: " % os.environ.get('S3_KEY'))
                        answer = sys.stdin.readline().rstrip()
                    if answer in ['Yes','yes','Y','y']:
                        self.options.key = os.environ.get('S3_KEY')
                    elif answer in ['No', 'no','N','n']:
                        exit("this does not look like a git folder, i can not auto determine key , and you forbid me to use the S3_KEY env, please use -k|-K option")
                    if answer in ['']:
                        self.options.key = os.environ.get('S3_KEY')

                elif 'S3_KEY' in os.environ and self.options.quiet == True:
                    self.options.key = os.environ.get('S3_KEY')
                else:
                    exit("this does not look like a git folder , can not auto determine key please -k option")
            else:
               self.options.key = self.key

        if 'S3_REGION' in os.environ and self.options.quiet == False:
            answer = 'UNDEF'
            while answer not in ['Yes','yes','No','no','Y','y','N','n','']:
                sys.stdout.write("S3_REGION seems to  be set to: \"%s\" , use this value? Y/N: " % os.environ.get('S3_REGION'))
                answer = sys.stdin.readline().rstrip()

            if answer in ['Yes','yes','Y','y']:
                self.options.region = os.environ.get('S3_REGION')
            elif answer in ['No', 'no','N','n']:
                exit("i can not auto determine bucket , pleas correct S3_BUCKET env var")
            if answer in ['']:
                self.options.region = os.environ.get('S3_REGION')

        elif 'S3_REGION' in os.environ and self.options.quiet == True:
            self.options.region = os.environ.get('S3_REGION')
        else:
            exit("this does not look like a git folder , can not auto determine region please -k option")

        if 'S3_BUCKET' in os.environ and self.options.quiet == False:
            answer = 'UNDEF'
            while answer not in  ['Yes','yes','No','no','Y','y','N','n','']:
                sys.stdout.write("S3_BUCKET seems to  be set to: \"%s\" , use this value? Y/N: " % os.environ.get('S3_BUCKET'))
                answer = sys.stdin.readline().rstrip()
            if answer in ['Yes','yes','Y','y']:
                self.options.bucket = os.environ.get('S3_BUCKET')
            elif answer in ['No', 'no','N','n']:
                exit("i can not auto determine bucket , pleas correct S3_BUCKET env var")
            if answer in ['']:
                self.options.bucket = os.environ.get('S3_BUCKET')

        elif 'S3_BUCKET' in os.environ and self.options.quiet == True:
            self.options.bucket = os.environ.get('S3_BUCKET')
        else:
            exit("this does not look like a git folder , can not auto determine bucket please -k option")

    def configure(self):
        if not os.path.exists(self.path+'.terraform'):
            self.build_configure_args()
            print "CONFIGURING TERRAFORM with opts: key: {}, region: {}, bucket: {}".format(self.options.key,
                                                                                            os.environ.get('S3_REGION'),
                                                                                            os.environ.get('S3_BUCKET'))
            args_plan = ["-backend=s3", 
                        "-backend-config=bucket="+self.options.bucket,
                        "-backend-config=region="+self.options.region,
                        "-backend-config=key="+self.options.key+"/"+self.relative_path+"/terraform.tfstate",
                    ]
            args_plan.insert(0,self.prog)
            args_plan.insert(1,'remote')
            args_plan.insert(2,'config')
            child = subprocess.call(args_plan)

        pass

    def run(self):
        # call this to run terraform plan
        # need to verify if .remote is configured first
        # creates lock file to prevent accident apply will use --force-apply to ingore and remove the local lock
        self.configure()
        self.args=sys.argv
        if 'plan' in self.args:
            self.plan()
        elif 'apply' in self.args:
            self.apply()
        else:
            self.plan()

    def plan(self):
        args_plan = [self.prog,'plan']
        child = subprocess.call(args_plan)

    def apply(self):
        args_plan = [self.prog,'apply']
        child = subprocess.call(args_plan)

    def chat_lock(self):
        # todo for v0.2 - create's chat lock 
        pass
    def chat_lock_release(self):
        # TODO FOR v0.2 - release chat lockl
        pass
    def chat_lock_force_release(self):
        # TODO FOR v0.2 - force release chat lock if  exists when --force-apply and call chat_locl_release()
        pass

if __name__ == "__main__":
    instance = terraform_this()
    instance.run()
