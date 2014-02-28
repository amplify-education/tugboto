#!/usr/bin/env python

# Amplify Education [www.amplify.com]
# Original author : tfisher@amplify.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DEBUG=False
VERSION = '0.01'

import argparse
import json
import mimetypes
import os
import subprocess
import sys

from datetime import datetime, timedelta

########################################################################
# Try to import boto, sending a helpful error message if we fail.
try:
	import boto
except:
	exit("importing boto failed.  try activating your virtualenv and/or `pip install boto`")

#importing as just s3 so it's clear where tugboto ends.
from boto import s3
from boto.s3.connection import S3Connection

def debug_message(message_type='debug', *args):
	'''
	output the debugging message as JSON
	'''
	return json.dumps({message_type: args})


class TugBoto_S3(object):

	def __init__(self, aws_access_secret, aws_access_key, bucket_name=None, directory_name=None):
		self.aws_access_secret = aws_access_secret
		self.aws_access_key = aws_access_key
		self.bucket_name = bucket_name
		self.directory_name = directory_name
		self.connection = S3Connection(AWS_KEY,AWS_SECRET)
		self.key_list = bucket_name.get_all_keys(prefix=directory_name)
		self.key_list_content = []

	def cp(self):
		print "aws cp"

	def expire(self, days):
		days = int(days)

		for key in self.key_list:
			content_type, unused = mimetypes.guess_type(key.name)
			if not content_type:
				content_type = 'text/plain'
			expire_time =  datetime.utcnow() + timedelta(days=(days))
			expire_time = expire_time.strftime(("%a, %d %b %Y %H:%M:%S GMT"))
			metadata = {'Expires': expire_time, 'Content-Type': content_type}

			if DEBUG: debug_message(key.name, metadata)

			self.key_list_content.append(key)
			key.copy(self.bucket_name, key, metadata=metadata, preserve_acl=True)


	def ls(self):
		'''
		list files from here in case a user doesn't know names.
		should be default if the bucket-name is none
		'''
		print "aws s3 ls"

	def show_version(self): print(VERSION)


########################################################################

if __name__ == "__main__":

	#Parse command line:
	parser = argparse.ArgumentParser(description="TugBoto tools for working with S3")
	parser.add_argument("-a", "--access-key", default=os.environ.get("AWS_ACCESS_KEY_ID"),
						help = "AWS Access Key ID", type = str)
	parser.add_argument("-s", "--access-secret", default=os.environ.get("AWS_SECRET_ACCESS_KEY"),
						help = "AWS Access Key Secret", type = str)
	parser.add_argument("-r", "--instance_region", nargs=1, default="us-east-1", type=str,
						help="the region to query or 'all' for all regions [defaults to us-east-1]")
	parser.add_argument("-b", "--bucket", nargs=1, type=str )
	parser.add_argument("-d", "--directory", nargs=1, type=str )
	parser.add_argument("-e", "--expire-days", default=30, type=int,
						help = "Set the number of days before Amazon expires (deletes) content in the bucket")
	args = parser.parse_args()

	#Use the key specified by the command line or go hunting for it:
	AWS_KEY         =   args.access_key
	AWS_SECRET      =   args.access_secret
	if AWS_KEY is None: AWS_KEY = boto.config.get("Credentials", "aws_access_key_id")
	if AWS_SECRET is None: AWS_SECRET = boto.config.get("Credentials", "aws_secret_access_key")

	if AWS_KEY is None or AWS_SECRET is None:
		try:
			with open('../tugboto.conf', 'r') as TUGBOTO_CONFIG:
				TUGBOTO_CONFIG = json.load(TUGBOTO_CONFIG)
				if AWS_KEY is None: AWS_KEY = TUGBOTO_CONFIG['AWS_SECRET_KEY']
				if AWS_SECRET is None: AWS_SECRET = TUGBOTO_CONFIG['AWS_ACCESS_KEY']
		except IOError: pass

	#If the user didn't specify an action, politely exit
	if len(sys.argv) < 2:
		try: sys.exit(subprocess.call([__file__,"--help"])) #a hack but it works for now
		except: raise SystemExit('')
	else:
		tugboto = TugBoto_S3(
			aws_access_secret=AWS_SECRET,
			aws_access_key=AWS_KEY
		)
		tugboto.expire(days='15')