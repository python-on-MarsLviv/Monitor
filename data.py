import pickle
from os.path import join
import logging.config
from logger import logger_config

logging.config.dictConfig(logger_config)
logger = logging.getLogger('app_logger')

class Data(object):
	''' singelton to store share album data '''
	names = []
	encodings = []
	pictures = []
	length = 0
	pressed = ''
	def __new__(cls, path='data', file='encodings.pickle'):
		if not hasattr(cls, 'instance'):
			cls.instance = super(Data, cls).__new__(cls)
			cls.instance.data(path=path, file=file)
		return cls.instance

	def data(self, path='data', file='encodings.pickle'):
		if file != '':
			try:
				path_to_data_file = join(path, file)
				data = pickle.loads(open(path_to_data_file, "rb").read())
				Data.names = data['names']
				Data.encodings = data['encodings']
				Data.pictures = data['pictures']
				Data.length = len(Data.names)
			except:
				logger.info('Could not open data file')
				#print('Could not open data file')

	def save(self, path='data', file='encodings.pickle'):
		try:
			data = {"names": Data.names, "encodings": Data.encodings, "pictures": Data.pictures}
			path_to_data_file = join(path, file)
			f = open(path_to_data_file, "wb")
			f.write(pickle.dumps(data))
			f.close()
		except:
			logger.info('Could not save data file')
			#print('Could not save data file')

if __name__ == "__main__":
	# test class
	obj1 = Data('data', 'encodings.pickle')
	print('len 0', obj1.length, '   names 0', obj1.names)
	obj1.length = 60
	print('len 1', obj1.length, '   names 1', obj1.names)
	del obj1

	obj2 = Data('data', 'encodings.pickle')
	print('len 2', obj2.length, '   names 2', obj2.names)
