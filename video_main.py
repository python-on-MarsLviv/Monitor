from imutils.video import FileVideoStream
from imutils.video import VideoStream
from videostream import VideoStream as VideoStream1
from imutils import resize
from imutils import face_utils

import cv2

from os.path import join
from queue import Queue
from numpy import array
from time import sleep, perf_counter, time
from datetime import datetime
from threading import Thread
from multiprocessing import Process
from multiprocessing import Queue as  multiprocessing_Queue

# custom modules
from face_locator import face_locator
from save_video import Save_video

from config_params import ConfigParams
config = ConfigParams()

from data import Data
album  = Data(config.data[0]['path_to_data_file'], config.data[0]['encoding_file'])

import logging.config
from logger import logger_config

logging.config.dictConfig(logger_config)
logger = logging.getLogger('app_logger')
monitor = logging.getLogger('app_monitor')

class VideoMain():
	def init_tools(self, **kwargs):
		self.output_queue = kwargs['output_queue']

		self.camera = config.data[0]['camera']

		self.fps = 5
		self.max_fps = 20
		self.min_fps = 3

		self.fake_frame = array([1,1,1,3])

		self.looping = False 				# flag to show that start_process_loop() method running

		self.err_read_frame = False 		# error occured during frame reading
		self.err_processing_frame = False	# error occured during frame processing

		self.names_known = album.names
		self.encodings_known = album.encodings

		self.p_to_work = True   			# flag to allow/disallow Processes work
		self.process_0_face_locator = None
		self.process_1_face_locator = None
		self.process_2_face_locator = None
		self.process_video_saver = None

		self.text_for_tablo = ''
		self.list_for_tablo = []

		self.tracking_names = []

		self.video_saver = Save_video()

	def start_stream(self):
		self.vs.start()

	def stop_stream(self):
		self.vs.stop()

	def init_stream(self, camera=0):
		if type(camera) == type(1):
			self.camera = camera;
			self.web_cam = True
			self.file = ''
			try: 
				self.vs = VideoStream1(self.camera)
				self.err_open_stream = False
			except:
				self.err_open_stream = True
				logger.info('can not open stream')
		elif type(camera) == type('string'):
			self.camera = -1;
			self.web_cam = False 		
			self.file = camera
			try:
				self.vs = FileVideoStream(self.file)
				self.err_open_stream = False
			except:
				self.err_open_stream = True
				logger.info('can not open file')

		#sleep(0.1)						# time to worm-up camera	

	def stop_process_loop(self):
		self.thread_process_loop.join()

	def start_process_loop(self):
		time_init = perf_counter()
		self.looping = True

		temp_frame = None; temp_names = None; temp_time_grab = None
		queue_process2main = Queue(maxsize=0)

		p_locating = 0; p_tracking = -1
		next_base_frame = False
		self.px_status = ['locating', 'ready', 'ready']
		active_frames = [0, 0, 0]

		# flexible fps rate achiving. keeping 70% face-locator Processes loading
		frame_koef = 0
		loop_delay = 0

		first_frame = True

		while  self.looping:
			# if this is a file video stream, then we need to check if
			# there any more frames left in the buffer to process
			if not self.web_cam and not self.vs.more():
				logger.info('web cam terminated')
				break

			try:
				frame = self.vs.read()
				frame_time = datetime.now()
				time_grab = perf_counter()
			except:
				self.err_read_frame = True
				logger.info('can not read frame')
				continue

			### flexible fps
			prev_fps = self.fps

			# reduce fps because of big computational time
			self.fps = self.fps + int(self.fps * frame_koef)
			# reduce fps because of big loop delay
			loop_koef = 0
			if loop_delay > 5 and loop_delay <= 10:
				loop_koef = 1
			elif loop_delay > 10 and loop_delay <= 15:
				loop_koef = 2
			elif loop_delay > 15:
				loop_koef = 3
			loop_delay = 0
			self.fps = self.fps - loop_koef

			# keep fps in sane range
			if self.fps < self.min_fps:
				self.fps = self.min_fps
			elif self.fps > self.max_fps:
				self.fps = self.max_fps
			frame_koef = 0
			### /flexible fps

			# keep frame rate acording to fps
			if (time_grab - time_init) < (1 / self.fps):
				continue

			time_init = time_grab

			try:
				quality_width = int(frame.shape[1] * config.data[0]['quality'])
			except:
				logger.info('frame not available')
				break
			
			if self.p_to_work:
				frame = resize(frame, width=quality_width)

				if config.data[0]['mark_frames']:
					cv2.putText(frame, str(frame_time), (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

				# handle Tracing2Ready change
				if active_frames[p_tracking % 3] == 0 and self.px_status[p_tracking % 3] == 'tracking':
					self.px_status[p_tracking % 3] = 'ready'
					#print('track 2 ready, self.px_status:{}:'.format(self.px_status))

				# handle Locating2Tracking change
				n_frames = self.output_queues[p_locating % 3].qsize()
				if self.px_status[p_locating % 3] == 'locating' and n_frames:
					self.px_status[p_locating % 3] = 'tracking'
					#print('locate 2 track, self.px_status:{}:'.format(self.px_status))

				# handle Rrady2Locating change
				if self.px_status[p_locating % 3] == 'tracking' and self.px_status[(p_locating+1) % 3] == 'ready':
					self.px_status[(p_locating+1) % 3] = 'locating'
					p_locating += 1											# L - increasing locator Process number
					#print('ready 2 locate, self.px_status:{}:, p_locating += 1:{}:'.format(self.px_status, p_locating))
				
				if active_frames[p_tracking % 3] == 0 and self.px_status[(p_tracking+1) % 3] == 'tracking':
					next_base_frame = True
					p_tracking += 1											# T - increasing tracker Process number
					#print('p_tracking += 1:{}:'.format(p_tracking))

				# handle locating
				if self.px_status[p_locating % 3] == 'locating':
					self.input_queues[p_locating % 3].put((frame, config.data[0]['mark_frames'], time_grab))
					active_frames[p_locating % 3] += 1

				# handle tracking
				if self.px_status[p_tracking % 3] == 'tracking':
					n_frames = self.output_queues[p_tracking % 3].qsize()
					for i_frames in range(n_frames):
						(temp_frame, temp_names, frame_koef, temp_time_grab) = self.output_queues[p_tracking % 3].get()
						#self.compare_names(temp_names)
						queue_process2main.put((temp_frame, temp_time_grab))
						active_frames[p_tracking % 3] -= 1
					# define loop delay = delay to propagate frame from grab to push
					loop_delay = int(time_grab - temp_time_grab)
					#print('loop_delay:{:.2f}'.format(loop_delay))


					# some changes in names only once - when augmentation in Process tracking (p_tracking += 1)
					# so there is sence to compare names only in this cases
					if next_base_frame:
						self.compare_names(temp_names)
					#print('got {} frames'.format(n_frames))

				# save base frame to picture file / save base frame to video file

				# save base frame to picture file
				if next_base_frame and config.data[0]['save_monitor_picture']:
					file = 'base_frame_{}.jpg'.format(temp_time_grab)
					folder = config.data[0]['path_to_base_frames']
					try:
						cv2.imwrite(join(folder, file), temp_frame)
					except:
						logger.info('could not write base frame')

				# save base frame to video file

				# write previous bunch to file and start new one
				if (next_base_frame or first_frame) and config.data[0]['save_monitor_video']:
					file = 'base_frame_bunch_{}.avi'.format(temp_time_grab)
					folder = config.data[0]['path_to_video']
					# temp_frame is None from initialization up to first frame got from Processes 0-2
					if temp_frame is not None:
						self.video_saver_file_name_queue.put((join(folder, file), temp_frame))
				# add regular frame to bunch
				elif not next_base_frame and config.data[0]['save_monitor_video']:
					if temp_frame is not None:
						self.video_saver_frame_queue.put(temp_frame)

				next_base_frame = False
				first_frame = False
				# /save base frame to picture file and save base frame to video file

			# avoid overflowing
			if p_locating == 3000:
				p_locating = p_locating % 3
				p_tracking = p_tracking % 3

			if not self.output_queue.full() and queue_process2main.qsize():
				if config.data[0]['show_video']:
					temp_frame_out, temp_time_grab_out = queue_process2main.get()
					self.output_queue.put((self.fps, temp_frame_out, temp_time_grab_out))
				else:
					self.output_queue.put((self.fps, self.fake_frame, temp_time_grab_out))

			if not self.processes_is_alive(): # err 200
				logger.info('some Process dead')
				

		self.vs.stop();

	def set_camera(self, camera):
		self.camera = camera

	@staticmethod
	def get_registered_cameras():
		cameras = []
		for i in range(10):
			stream = cv2.VideoCapture(i)
			if stream is None or not stream.isOpened():
				stream.release()
				return cameras
			else:
				cameras.append(i)
				stream.release()

		return cameras
	
	def start(self, camera=0):
		if not self.looping:
			self.p_to_work = True
			self.init_stream(camera)
			self.thread_process_loop = Thread(target=self.start_process_loop, args=())
			#self.thread_process_loop.daemon = True # https://github.com/jrosebr1/imutils/issues/38
			self.start_stream()
			self.thread_process_loop.start()

			self.video_saver_exit_queue = multiprocessing_Queue()
			self.video_saver_frame_queue = multiprocessing_Queue()
			self.video_saver_file_name_queue = multiprocessing_Queue()

			self.p0_input_queue = multiprocessing_Queue()
			self.p0_output_queue = multiprocessing_Queue()
			self.p0_exit_queue = multiprocessing_Queue()
			self.p0_tracking_names_queue = multiprocessing_Queue()
			self.p1_input_queue = multiprocessing_Queue()
			self.p1_output_queue = multiprocessing_Queue()
			self.p1_exit_queue = multiprocessing_Queue()
			self.p1_tracking_names_queue = multiprocessing_Queue()
			self.p2_input_queue = multiprocessing_Queue()
			self.p2_output_queue = multiprocessing_Queue()
			self.p2_exit_queue = multiprocessing_Queue()
			self.p2_tracking_names_queue = multiprocessing_Queue()

			self.input_queues = [self.p0_input_queue, self.p1_input_queue, self.p2_input_queue]
			self.output_queues = [self.p0_output_queue, self.p1_output_queue, self.p2_output_queue]

			
			self.process_0_face_locator = Process(target=face_locator, args=(self.names_known, self.encodings_known \
				, None, None, self.p0_input_queue, self.p0_output_queue, self.p0_exit_queue, self.p0_tracking_names_queue))
			self.process_0_face_locator.start()

			self.process_1_face_locator = Process(target=face_locator, args=(self.names_known, self.encodings_known \
				, None, None, self.p1_input_queue, self.p1_output_queue, self.p1_exit_queue, self.p0_tracking_names_queue))
			self.process_1_face_locator.start()

			self.process_2_face_locator = Process(target=face_locator, args=(self.names_known, self.encodings_known \
				, None, None, self.p2_input_queue, self.p2_output_queue, self.p2_exit_queue, self.p0_tracking_names_queue))
			self.process_2_face_locator.start()

			self.process_video_saver = Process(target=self.video_saver.do_work, \
				args=(self.video_saver_exit_queue, self.video_saver_frame_queue, self.video_saver_file_name_queue))
			self.process_video_saver.start()

			if not self.processes_is_alive():
				self.stop()
				return

			monitor.info('Monitor started')
			self.text_for_tablo = 'Monitor started\nApplication started'
			self.list_for_tablo.append('Monitor started')
			self.list_for_tablo.append('Application started')

	def stop(self):

		self.p_to_work = False
		self.looping = False

		if self.process_0_face_locator.is_alive():
			self.p0_exit_queue.put(True)
		else:
			self.clean_queues([self.p0_input_queue, self.p0_output_queue, self.p0_exit_queue, self.p0_tracking_names_queue])

		if self.process_1_face_locator.is_alive():
			self.p1_exit_queue.put(True)
		else:
			self.clean_queues([self.p1_input_queue, self.p1_output_queue, self.p1_exit_queue, self.p0_tracking_names_queue])

		if self.process_2_face_locator.is_alive():
			self.p2_exit_queue.put(True)
		else:
			self.clean_queues([self.p2_input_queue, self.p2_output_queue, self.p2_exit_queue, self.p0_tracking_names_queue])
		
		self.p0_exit_queue.close()
		self.p0_output_queue.close()
		self.p0_input_queue.close()
		self.p0_tracking_names_queue.close()
		self.p1_exit_queue.close()
		self.p1_output_queue.close()
		self.p1_input_queue.close()
		self.p1_tracking_names_queue.close()
		self.p2_exit_queue.close()
		self.p2_output_queue.close()
		self.p2_input_queue.close()
		self.p2_tracking_names_queue.close()
		
		self.p0_exit_queue.join_thread()
		self.p0_output_queue.join_thread()
		self.p0_input_queue.join_thread()
		self.p0_tracking_names_queue.join_thread()
		self.p1_exit_queue.join_thread()
		self.p1_output_queue.join_thread()
		self.p1_input_queue.join_thread()
		self.p1_tracking_names_queue.join_thread()
		self.p2_exit_queue.join_thread()
		self.p2_output_queue.join_thread()
		self.p2_input_queue.join_thread()
		self.p2_tracking_names_queue.join_thread()

		self.process_0_face_locator.join() # join dead process is safe
		self.process_1_face_locator.join()
		self.process_2_face_locator.join()
		logger.info('exiting, check 0 Process state:{}'.format(self.process_0_face_locator.is_alive()))
		logger.info('exiting, check 1 Process state:{}'.format(self.process_0_face_locator.is_alive()))
		logger.info('exiting, check 2 Process state:{}'.format(self.process_0_face_locator.is_alive()))

		if self.process_video_saver.is_alive():
			self.video_saver_exit_queue.put(True)
		else:
			self.clean_queues([self.video_saver_exit_queue, self.video_saver_frame_queue, self.video_saver_file_name_queue])
		
		self.video_saver_exit_queue.close()
		self.video_saver_frame_queue.close()
		self.video_saver_file_name_queue.close()

		self.video_saver_exit_queue.join_thread()
		self.video_saver_frame_queue.join_thread()
		self.video_saver_file_name_queue.join_thread()

		self.process_video_saver.join() # join dead process is safe
		logger.info('exiting, check video_saver Process state:{}'.format(self.process_video_saver.is_alive()))

		self.stop_process_loop()

		monitor.info('Monitor stopped')

	def compare_names(self, new_names):
		if new_names == self.tracking_names:
			return

		new_tracking_names = []
		was_change = False

		for name in new_names:
			if name in self.tracking_names:
				new_tracking_names.append(name)
			else:
				new_tracking_names.append(name)
				self.write_monitor_info('new person at area: {}'.format(name))
				was_change = True

		for name in self.tracking_names:
			if name not in new_names:
				self.write_monitor_info('person left area: {}'.format(name))
				was_change = True

		self.tracking_names = new_tracking_names

		if was_change:
			self.write_monitor_info('all persons at area: {}'.format(self.tracking_names))
			# push current names to Processes to speed up work
			# these names will be checked in first place
			names_to_processes = []
			for name_i in self.tracking_names:
				if name_i is not 'underfined':
					names_to_processes.append(name_i)

			self.p0_tracking_names_queue.put(names_to_processes)
			self.p1_tracking_names_queue.put(names_to_processes)
			self.p2_tracking_names_queue.put(names_to_processes)

	def clean_queues(self, queues):
		for queue in queues:
			while queue.qsize():
				_ = queue.get()

	def processes_is_alive(self):
		# Processes did not started yet
		if self.process_0_face_locator is None:
			return True

		if not self.process_0_face_locator.is_alive():
			logger.info('Process 0 could not start - exiting.')
			return False
		if not self.process_1_face_locator.is_alive():
			logger.info('Process 1 could not start - exiting.')
			return False
		if not self.process_2_face_locator.is_alive():
			logger.info('Process 2 could not start - exiting.')
			return False

		if not self.process_video_saver.is_alive():
			logger.info('Process video_saver could not start - exiting.')
			return False
		
		return True

	def write_monitor_info(self, message):
		# add info to monitor file
		monitor.info(message)

		# add info to tablo
		self.text_for_tablo = ''

		self.list_for_tablo.append(str(datetime.now()) + ': ' + message)
		while len(self.list_for_tablo) > 8:
			self.list_for_tablo.pop(0)

		for line in self.list_for_tablo:
			self.text_for_tablo += line
			self.text_for_tablo += '\n'

