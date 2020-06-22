import json
from os import mkdir
from os import getcwd
from os.path import join
from os.path import exists
from time import time

import logging.config
from logger import logger_config

logging.config.dictConfig(logger_config)
logger = logging.getLogger('app_logger')

class ConfigParams(object):
	''' class singelton to manage configuration '''

	# write default information into fields
	data = []
	data.append({
	    "version": 0.1,
	    "user_name": "user",
	    "camera": 0,
	    "quality": 0.75,
	    "show_video": 0,
	    "page": "train",
	    "monitor_on_start": 0,
	    "mark_frames": 1,
	    "save_monitor_picture": 0,
	    "save_monitor_video": 0,
	    "keep_log_file_days": 1,
	    "path_to_log_file": "log",
	    "path_to_data_file": "data",
	    "encoding_file": "encodings.pickle",
	    "path_to_monitor_file": "monitor",
	    "path_to_new_persons": "new_persons",
	    "path_to_base_frames": "base_frames",
	    "path_to_video": "path_to_video"
		})

	def __new__(cls):
		''' ensure just one instance of this class '''
		if not hasattr(cls, 'instance'):
			cls.instance = super(ConfigParams, cls).__new__(cls)
			cls.instance.config_file(file='config.json')
		return cls.instance

	def config_save(self, file='config.json'):
		''' save configratoion info'''
		try:
			with open(file, 'w') as f:
				ConfigParams.data[0]['HELP camera'] = 'Camera to use. 0 - built-in, 1 - plugged, etc'
				ConfigParams.data[0]['HELP quality'] = 'Reduce captured image. Value in [0.25 0.5 0.75 1] -> [worse_quality better_quality]'
				ConfigParams.data[0]['HELP show_video'] = 'Value in [0 1]'
				ConfigParams.data[0]['HELP page'] = 'Value in [train monitor]'
				ConfigParams.data[0]['HELP monitor_on_start'] = 'Value in [0 1]'
				ConfigParams.data[0]['HELP mark_frames'] = 'Value in [0 1]'
				ConfigParams.data[0]['HELP save_monitor_picture'] = 'Value in [0 1]'
				ConfigParams.data[0]['HELP save_monitor_video'] = 'Value in [0 1]'
				ConfigParams.data[0]['HELP keep_log_file_days'] = 'Value in [1 .. 365]'
				ConfigParams.data[0]['HELP path_to_log_file'] = 'path to log file'
				ConfigParams.data[0]['HELP path_to_data_file'] = 'path_to_data_file'
				ConfigParams.data[0]['HELP encoding_file'] = 'name of encoding file; by default <encodings.pickle>'
				ConfigParams.data[0]['HELP path_to_monitor_file'] = 'path_to_monitor_file'
				ConfigParams.data[0]['HELP path_to_new_persons'] = 'path_to_new_persons picture'
				ConfigParams.data[0]['HELP path_to_base_frames'] = 'path_to_base_frames folder'
				ConfigParams.data[0]['HELP path_to_video'] = 'path_to_video folder'
				json.dump(ConfigParams.data[0], f, indent=4)
		except:
			logger.info('Could not save configuration file')

	def config_file(self, file='config.json'):
		''' format configratoion info'''
		try:
			with open(file, 'r') as f:
				ConfigParams.data.append(json.load(f))
		except:
			logger.info('Could not load configuration file. Using default parameters')
			return
		
		# parse all keys
		if ConfigParams.data[1]['camera'] in [0, 1, 2]:
			ConfigParams.data[0]['camera'] = ConfigParams.data[1]['camera']
		if ConfigParams.data[1]['quality'] in [.25, .5, .75, 1.0]:
			ConfigParams.data[0]['quality'] = ConfigParams.data[1]['quality']
		if ConfigParams.data[1]['show_video'] in [0, 1]:
			ConfigParams.data[0]['show_video'] = ConfigParams.data[1]['show_video']
		if ConfigParams.data[1]['page'] in ["train", "monitor"]:
			ConfigParams.data[0]['page'] = ConfigParams.data[1]['page']
		if ConfigParams.data[1]['monitor_on_start'] in [0, 1]:
			ConfigParams.data[0]['monitor_on_start'] = ConfigParams.data[1]['monitor_on_start']
		if ConfigParams.data[1]['mark_frames'] in [0, 1]:
			ConfigParams.data[0]['mark_frames'] = ConfigParams.data[1]['mark_frames']
		if ConfigParams.data[1]['save_monitor_picture'] in [0, 1]:
			ConfigParams.data[0]['save_monitor_picture'] = ConfigParams.data[1]['save_monitor_picture']
		if ConfigParams.data[1]['save_monitor_video'] in [0, 1]:
			ConfigParams.data[0]['save_monitor_video'] = ConfigParams.data[1]['save_monitor_video']
		if ConfigParams.data[1]['keep_log_file_days'] >= 1 and ConfigParams.data[1]['keep_log_file_days'] <= 365:
			ConfigParams.data[0]['keep_log_file_days'] = ConfigParams.data[1]['keep_log_file_days']

		self.make_dir(ConfigParams, 'path_to_log_file')
		self.make_dir(ConfigParams, 'path_to_data_file')
		self.make_dir(ConfigParams, 'path_to_monitor_file')
		self.make_dir(ConfigParams, 'path_to_new_persons')
		self.make_dir(ConfigParams, 'path_to_base_frames')
		self.make_dir(ConfigParams, 'path_to_video')

		if ConfigParams.data[0]['encoding_file'] == '':
			pass
		else:
			path_to_data_file = join(ConfigParams.data[1]['path_to_data_file'], ConfigParams.data[1]['encoding_file'])
			if exists(path_to_data_file):
				ConfigParams.data[0]['encoding_file'] = ConfigParams.data[1]['encoding_file']
			else:
				logger.info("Encoding file {} not exist.".format(path_to_data_file))
				ConfigParams.data[0]['encoding_file'] = ''
		
	def make_dir(self, ConfigParams, dir):
		''' creates drectory <dir> if not exist and write it to configuration '''
		path = join(getcwd(), ConfigParams.data[1][dir])
		if exists(path):
			ConfigParams.data[0][dir] = path
		else:
			try:
				mkdir(path)
				ConfigParams.data[0][dir] = path
			except OSError:
				logger.info('Creation of the directory {} failed'.format(path))
				path = join(path, '_', str(int(time())))
				mkdir(path)
				ConfigParams.data[0][dir] = path
			except:
				logger.info('Creation of the directory {} failed. Exiting.'.format(path))

# can be tested
# python config_params.py
if __name__ == "__main__":
	s = ConfigParams()
	s1 = ConfigParams()

	s.data[0]['user_name'] = '100'
	print(s.data[0]['user_name'])
	print(s1.data[0]['user_name'])
		

