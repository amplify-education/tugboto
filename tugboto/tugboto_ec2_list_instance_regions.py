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

import os
import re
import argparse

####################################
try:
	import boto.ec2
	import boto.vpc
except:
	exit("importing boto failed.  try activating your virtualenv and/or `pip install boto`")

#Parse command line:
parser = argparse.ArgumentParser(description='get EC2 instance types per region')
parser.add_argument('-a', '--access-key', default=os.environ.get('AWS_ACCESS_KEY_ID'),
					help = "AWS Access Key ID", type = str)
parser.add_argument('-s', '--access-secret', default=os.environ.get('AWS_SECRET_ACCESS_KEY'),
					help = "AWS Access Key Secret", type = str)
parser.add_argument('-r','--instance_region', nargs=1, default='us-east-1', type=str,
					help="the region to query or 'all' for all regions [defaults to us-east-1a]")
parser.add_argument('-p','--instance_placement', nargs=1, type=str,
					help='the placement group to query [OPTIONAL]')
parser.add_argument('-t','--type', nargs=1, type=str, help='the instance type to seek [e.g. m1.medium]')
parser.add_argument('-d','--dictionary_item', nargs='*', type=str, help='include dictionary item X into the output. [OPTIONAL]')
args = parser.parse_args()

#By nature of os.environ.get
AWS_KEY         =   args.access_key
AWS_SECRET      =   args.access_secret
if AWS_KEY is None: AWS_KEY = boto.config.get('Credentials', 'aws_access_key_id')
if AWS_SECRET is None: AWS_SECRET = boto.config.get('Credentials', 'aws_secret_access_key')

####################################

def enumerate(instance_region=args.instance_region, instance_size=args.type, instance_placement=args.instance_placement,
			  aws_access_key_id=args.access_key, aws_secret_access_key=args.access_secret, dictionary_item=args.dictionary_item):

	instances = []
	bound_regional_ec2_conn = boto.ec2.connect_to_region(instance_region)

	try: dictionary_item = dictionary_item.pop() #until we have a need to iterate over a list of items
	except: pass

	if instance_size: search_filters = {'instance_type' : instance_size}
	else: search_filters = {}

	if len(instance_region) <= 1:
		instance_region = instance_region.pop()  #one item list handled as a str until multi-region is implemented

	if instance_region == 'all':

		for region in boto.ec2.regions():
			instances += [i for r in boto.vpc.VPCConnection(region=region).
				get_all_instances(filters=search_filters) for i in r.instances]

		for i in instances:
			try: hostname = str(i.tags['Name'])
			except:	hostname = ''
			try: tag = getattr(i, dictionary_item)
			except: tag = ''

			print(str(i._placement)+','+str(i.instance_type)+','+str(i.id) + ',' + hostname
				  + ',' + str(tag))

	else:

		if re.match('[a-z]', instance_region[-1:], re.IGNORECASE):
			print "Perhaps you included the placement with the region " \
				  "[e.g. us-east-1 and not us-east-1a]? Removing last character and attempting to continue..."
			instance_region = instance_region[:-1]

		def filter_region():

			#TODO: there's a way around this.  fix soon.
			if str(instance_region) != str('us-east-1'):
				exit( "You should use '-r all' to specify all regions for non us-east. Boto has some weirdness surrounding " \
					  "returning instances from non us-east-1 or whatever your default region happens to be." \
					  " Don't shoot the piano player. He'll fix it when Boto-Core provides a facility for returning from " \
					  "boto.(vpc|ec2).(VPC|EC2)Connection(region=my_var)" )

			instances = [ i for r in boto.ec2.EC2Connection(bound_regional_ec2_conn)
							.get_all_instances(filters=search_filters) for i in r.instances]
							#vpc and ec2 ostensibly are still handled differently

			if len(instances) == 0:
				exit("No instances found...")

			if instance_placement:
				if len(instance_placement) == 1:
					placement = instance_placement.pop()
				for i in instances:
					try: hostname = str(i.tags['Name'])
					except:	hostname = ''
					try: tag = getattr(i, dictionary_item)
					except: tag = ''
					if (str(i._placement) == str(placement)):
						print (str(i._placement) + ',' + str(i.instance_type) + ',' + str(i.id) + ',' + str(hostname)
							   + ',' + str(tag))
			else:
				for i in instances:
					try: hostname = str(i.tags['Name'])
					except:	hostname = ''
					try: tag = getattr(i, dictionary_item)
					except: tag = ''
					print (str(i._placement) + ',' + str(i.instance_type) + ',' + str(i.id) + ',' + str(hostname)
						+ ',' + str(tag))

		if instance_region == 'all': pass
		elif instance_region: filter_region()

####################################

if args.instance_region:
	try:
		enumerate(instance_region=args.instance_region, instance_size=args.type, instance_placement=args.instance_placement)
	except: #This happens if boto can't build a connection to the region.  Will get triggered normally because
			#of default on region flag.
		parser.print_help()
		exit()
