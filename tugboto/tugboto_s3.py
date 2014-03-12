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

#TODO: lowercase all the input
#TODO: implement a lookup dict the TugBoto_S3 methods and add a print flag?
#TODO: this is in a weird module/script state -- replace prints with return and print on the __name__ == '__main__'

raise NotImplementedError('not ready quite yet.')

VERSION = '0.03'

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
except ImportError:
	exit("importing boto failed.  try activating your virtualenv and/or `pip install boto`")

#importing as just s3 so it's clear where tugboto ends.
from boto import s3
from boto import connect_s3
from boto.s3.connection import S3Connection, Location
from boto.s3.lifecycle import Lifecycle, Expiration, Transition, Rule
from boto.s3.key import Key

############################################################
# Helpers for use as a script
############################################################

def confirm(message="Are you sure? [y/n]: "):
	response = str(raw_input(message)).lower()
	if response == 'y': return True
	else: return False


#if this is being run as a script, use system exit codes
if __name__ == '__main__':
	_success = exit(0)
	_failure = exit(1)
else:
	_success = True
	_failure = False

def debug_message(message_type='debug', *args):
	'''
	output the debugging message as JSON
	'''
	return json.dumps({message_type: args})

############################################################

class TugBoto_S3(object):

	def __init__(self, aws_access_secret, aws_access_key, bucket_name=None, key_name=None, location='', debug=False):
		self.aws_access_secret = aws_access_secret
		self.aws_access_key = aws_access_key
		self.bucket_name = bucket_name
		self.key_name = key_name

		# An empty string is interpreted to mean 'the original s3 region', so let's just specify it.
		if location in ('USEast' or 'classic' or ''): location = 'DEFAULT'

		#filter out the locations from the magic methods and see if the specified location is in the API
		valid_datacenters = [ datacenter for datacenter in dir(Location) if datacenter[0].isupper()]
		if location in valid_datacenters: self.location = location
		else: raise SystemExit('Valid datacenters are: {0}'.format(' '.join(valid_datacenters)))

		self.connection = S3Connection(AWS_KEY, AWS_SECRET)
		self.bucket = self.connection.get_bucket(bucket_name)
		self.key_list = self.bucket.get_all_keys(prefix=key_name)
		self.key_list_content = []
		self.debug = debug

	def cp(self):
		print "aws cp"

	def expire(self, days, transition):
		self.days = int(days)
		self.transition = transition
		#using nargs in ArgumentParser leads to passing lists, use the robustness principle
		if type(self.transition) == list: self.transition = str(self.transition[0])

		if self.transition == 'delete':
			pass

		if self.transition == 'glacier':
			lifecycle = Lifecycle()
			lifecycle_action = Transition(days=self.days, storage_class='GLACIER')

			rule = Rule('ruleid', 'logs/', 'Enabled', transition=lifecycle_action)
			lifecycle.append(rule)


		for key in self.key_list:
			content_type, unused = mimetypes.guess_type(key.name)
			if not content_type:
				content_type = 'text/plain'
			expire_time =  datetime.utcnow() + timedelta(days=(self.days))
			expire_time = expire_time.strftime(("%a, %d %b %Y %H:%M:%S GMT"))
			metadata = {'Expires': expire_time, 'Content-Type': content_type}

			if self.debug: debug_message(key.name, metadata)

			self.key_list_content.append(key)
			key.copy(self.bucket_name, key, metadata=metadata, preserve_acl=True)

		#Give the user a head's up of what was run (if we're here, we didn't make a Traceback):
		if self.debug: print debug_message('debug', "bucket: {x.bucket_name}, policy: {x.transition}, days: {x.days}".format(x=self))

	def show_lifecycle(self):
		current_lifecycle = self.bucket.get_lifecycle_config()
		print current_lifecycle[0].transition

	def make(self):
		self.connection.create_bucket(self.bucket_name, location=self.location)


	def ls(self, scope='all'):
		'''
		list all the buckets if the object_type is 'all', else: list the keys in a specified bucket
		'''
		if scope=='all':
			print self.connection.get_all_buckets()
		else:
			print self.bucket.list()

	def rm(self, key_name):
		k = Key(self.bucket)
		k.key = key_name
		k.delete()

	def rm_bucket(self, bucket):

		if __name__ == '__main__':
			if confirm("This will remove all keys in the bucket. Are you sure? [y/n]:"):
				for k in self.bucket: k.delete()
				self.connection.delete_bucket(self.bucket)
			else:
				print "Cancelled."
				return _success

	'''
	todo: dry this up!  lookup dictionary or if action in (a,b,c) could handle this

	Key operations:
	'''

	def check_if_exists(self, key_name):

		if self.bucket.get_key(key_name): return _success
		else: return _failure

	def read(self, key_name):
		'''
		read a key from an S3 bucket, sending the contents to standard output
		'''
		k = Key(self.bucket)
		k.key = key_name
		k.get_contents_as_string()

	def fetch(self, key_name, filename):
		'''
		fetch a file from S3
		'''
		k = Key(self.bucket)
		k.key = key_name
		k.get_contents_to_filename(filename)

	def touch(self, key_name):
		'''
		touch a file with empty contents in S3
		'''
		k = Key(self.bucket)
		k.key = key_name
		k.set_contents_from_string('')

	def write(self, key_name, filename):
		'''
		write to a key in a specified bucket reading from a file
		'''
		k = Key(self.bucket)
		k.key = key_name
		k.set_contents_from_filename(filename)

	def show_version(self):
		print(VERSION)


########################################################################

if __name__ == "__main__":

	#todo: ideally, the layout would be:
	#tugboto_s3 ls or tugboto_s3 read -b 'bucket_name' -k 'key_name'

	#Parse command line:
	parser = argparse.ArgumentParser(description="TugBoto tools for working with S3")
	parser.add_argument("-d", "--debug", action='store_true', default=False)
	parser.add_argument("-a", "--access-key", default=os.environ.get("AWS_ACCESS_KEY_ID"),
						help = "AWS Access Key ID", type = str)
	parser.add_argument("-s", "--access-secret", default=os.environ.get("AWS_SECRET_ACCESS_KEY"),
						help = "AWS Access Key Secret", type = str)
	parser.add_argument("-r", "--instance-region", nargs=1, default="us-east-1", type=str,
						help="the region to query or 'all' for all regions [defaults to us-east-1]")
	#TODO: remove required from here.  not required for ls
	parser.add_argument("-b", "--bucket", nargs=1, type=str, required=True, help="target bucket for policy" )
	parser.add_argument("-k", "--key", nargs=1, type=str, help="optionally specify a key within the specified bucket" )
	parser.add_argument("-t", "--transition", nargs=1, type=str, choices=('delete', 'glacier'), default='delete')
	parser.add_argument("-e", "--expire-days", default=30, type=int,
						help = "Set the number of days before Amazon expires (deletes) content in the bucket")
	args = parser.parse_args()
	# Convert the arg object to a dict
	args = vars(args)

	#Use the key specified by the command line or go hunting for it:
	AWS_KEY         =   args['access_key']
	AWS_SECRET      =   args['access_secret']
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
			aws_access_key=AWS_KEY,
			bucket_name=args['bucket'][0],
			key_name=args['key'],
			debug=args['debug']
		)
		#TODO: implementing a lookup dict for non-init attributes would allow for
		#*arg,**kwarg passing
		if args['expire_days']:
			tugboto.expire(days=args['expire_days'], transition=args['transition'])