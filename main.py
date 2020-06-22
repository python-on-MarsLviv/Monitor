from kivy.config import Config

Config.set('graphics', 'height', '700');
Config.set('graphics', 'minimum_width', '600')
Config.set('graphics', 'minimum_height', '600')

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.core.image import Image
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.properties import ObjectProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.pagelayout import PageLayout
from kivy.logger import Logger

import re
import cv2
import face_recognition
import json
from time import time, perf_counter
from datetime import datetime
from numpy import array
from queue import Queue
from os.path import join
from os import getpid
from threading import Thread

# custom modules
import video_main
from config_params import ConfigParams
config = ConfigParams()

from data import Data
album  = Data(config.data[0]['path_to_data_file'], config.data[0]['encoding_file'])

import logging.config
from logger import logger_config

logging.config.dictConfig(logger_config)
logger = logging.getLogger('app_logger')
monitor = logging.getLogger('app_monitor')

	
class Collage(GridLayout):
	''' part of GUI. For details see UML diagram '''

	#	use share data <album>
	def __init__(self, **kwargs):
		super(Collage, self).__init__(**kwargs)
		
		self.rows = 2
		self.size_hint=(None, 1)
		self.bind(minimum_width=self.setter('width'))
		
		# formating names for Buttons
		names = ['New person']
		for  i in range(1, album.length + 1):
			names.append(album.names[i - 1])
		
		if len(names) < 20:
			for i in range(len(names), 20):
				names.append('New person')

		for i in range(len(names)):
			btn = ToggleButton(text=names[i], size_hint=(None, 1) , width=200 \
				, group='persons', on_press=self.on_press_button \
				, on_release=self.on_release_button)
			if i == 0:
				btn.state='down'
				album.pressed = 'New person'
			self.add_widget(btn)

	def on_press_button(self, instance):
		self.press_button(instance)
		
	def press_button(self, instance):
		instance.state = 'down'

	def on_release_button(self, instance):
		album.pressed = instance.text

class Pages(PageLayout):
	''' part of GUI. For details see UML diagram '''
	def __init__(self, **kwargs):
		super(Pages, self).__init__(**kwargs)

class Page1(BoxLayout):
	''' part of GUI. For details see UML diagram '''

	#	use share data <album>
	def __init__(self, **kwargs):
		super(Page1, self).__init__(**kwargs)
		Window.bind(on_dropfile=self.on_dropfile)

	def on_dropfile(self, widget, image_path):
		if album.pressed == 'New person':
			name = self.link_to_text_input.text
			if not re.match(r'\w+ *\w+', name) or len(name) > 30:
				self.link_to_info_label.text = 'In name allowed alphabetical, numerical, whitespace chars only.'
				return

			if name in album.names:
				self.link_to_info_label.text = 'This name on album already. Type other'
				return

		try:
			image = cv2.imread(image_path.decode('UTF-8'))
			rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
		except:
			self.link_to_info_label.text = 'Couldn\'t open file. Try other picture'
			return
		
		boxes = face_recognition.face_locations(rgb, model='hog') # can be 'hog' or 'cnn'
		encodings = face_recognition.face_encodings(rgb, boxes)

		if len(boxes) == 0:
			self.link_to_info_label.text = 'No person detected. Try other picture'
			return
		elif len(boxes) > 1:
			self.link_to_info_label.text = 'Detected more then one person. Try other picture'
			return
		else:
			if album.pressed == 'New person':
				album.names.append(name)
				album.encodings.append(encodings)
				album.pictures.append(image)
				album.length += 1
				self.link_to_info_label.text = '{} detected and added to album'.format(name)

				scrollview = self.children[0]
				collage = scrollview.children[0]
				counter = 0
				for child in collage.children:
					if child.text == 'New person':
						counter += 1
					if counter == 2:
						child.text = name
						break
				if counter == 1:
					btn = ToggleButton(text=name, size_hint=(None, 1) , width=200 \
						, group='persons', on_press=collage.on_press_button \
						, on_release=collage.on_release_button)
					collage.add_widget(btn)

			else:
				idx = album.names.index(album.pressed)
				album.encodings[idx].append(encodings[0])
				album.pictures[idx] = image
				self.link_to_info_label.text = 'One encodings added for {}'.format(album.pressed)

class Page2(BoxLayout):
	''' part of GUI. For details see UML diagram '''

	#	use share data <config>
	def __init__(self, **kwargs):
		super(Page2, self).__init__(**kwargs)

	def on_slider_quality(self, value):
		config.data[0]['quality'] = value / 100

	def on_show_video(self, value):
		self.link_to_btn_show_video.text = 'Show video' \
			if self.link_to_btn_show_video.text == 'Hide video' else 'Hide video'
		config.data[0]['show_video'] = 1 if config.data[0]['show_video'] == 0 else 0

	def on_checkbox_mark_click(self, active):
		config.data[0]['mark_frames'] = 1 if active else  0

	def on_checkbox_click_video(self, active):
		config.data[0]['save_monitor_video'] = 1 if active else  0

	def on_checkbox_click_picture(self, active):
		config.data[0]['save_monitor_picture'] = 1 if active else  0

class Container(BoxLayout):
	''' main part of GUI. For details see UML diagram '''

	#	use share data <album, config>
	link_to_pages = ObjectProperty(None)
	def __init__(self, **kwargs):
		super(Container, self).__init__(**kwargs)

		self.link_to_pages.link_to_page2.link_to_btn_show_video.text = 'Hide video' \
						if config.data[0]['show_video'] == 1 else 'Show video'
		self.link_to_pages.link_to_page2.link_to_slider_quality.value = config.data[0]['quality'] * 100
		self.link_to_pages.link_to_page2.link_to_check_box_marking.active = config.data[0]['mark_frames']
		self.link_to_pages.link_to_page2.link_to_check_box_video.active = config.data[0]['save_monitor_video']
		self.link_to_pages.link_to_page2.link_to_check_box_picture.active = config.data[0]['save_monitor_picture']
		self.link_to_pages.link_to_page2.link_to_btn_start_stop.text = 'Stop' \
						if config.data[0]['monitor_on_start'] else 'Start'
		self.link_to_pages.page = 0 \
						if config.data[0]['page'] == 'train' else 1
		self.link_to_monitoring.link_to_monitoring_file.text = \
			str('Monitor file: ' + join(ConfigParams.data[0]['path_to_monitor_file'], 'monitor_info.mon'))
		
		self.cameras_list = ['First camera', 'Second camera', 'Third camera']

		# big logo
		fake_array = array([1,1,1,3])
		# 	convert image to texture
		self.buf = cv2.flip(fake_array, 0).tostring()
		self.image_texture = Texture.create(size=(1, 1), colorfmt='bgr')
		self.image_texture.blit_buffer(self.buf, colorfmt='bgr', bufferfmt='ubyte')

		try:
			self.main_image_texture = Image('img/logo_big.png').texture
		except AttributeError:
			self.main_image_texture = AsyncImage(source='https://www.python.org/static/img/python-logo.png').texture
		except:
			self.main_image_texture = self.image_texture

		self.link_to_pages.link_to_page2.link_to_image.texture = self.main_image_texture
		# /big logo

		self.fps = None; self.image = None; self.p_time = None

	def init_tools(self, **kwargs):
		self.stream = kwargs['stream']
		self.output_queue = kwargs['output_queue']

	def transfer_frame(self):
		''' take frames, statistic info from Queue and display them '''
		qsize = self.output_queue.qsize()
		if not qsize:
			return
			
		# if queue with frames to long - skip some of them
		frames_to_skip = qsize // 10
		self.fps = 0
		for ii in range(frames_to_skip):
			(self.fps, self.image, self.p_time) = self.output_queue.get()

		(self.fps, self.image, self.p_time) = self.output_queue.get()
		self.link_to_pages.link_to_page2.link_to_fps_delay.text = 'fps: {}    delay: {:.2f} s'.format(self.fps, perf_counter() - self.p_time)
		
		try:
			if config.data[0]['show_video'] and self.stream.looping:
				# convert image to texture
				self.buf = cv2.flip(self.image, 0).tostring()
				self.image_texture = Texture.create(size=(self.image.shape[1], self.image.shape[0]), colorfmt='bgr')
				self.image_texture.blit_buffer(self.buf, colorfmt='bgr', bufferfmt='ubyte')
				self.link_to_pages.link_to_page2.link_to_image.texture = self.image_texture
			else:
				self.link_to_pages.link_to_page2.link_to_image.texture = self.main_image_texture
		except:
			pass
			#print('in transfer_frame: could not show frame')
		
		self.link_to_monitoring.link_to_monitoring_info.text = self.stream.text_for_tablo
		
	def on_start_stop(self, value):
		if self.link_to_pages.link_to_page2.link_to_btn_start_stop.text == 'Start':
			camera_num = self.cameras_list.index(self.link_to_pages.link_to_page2.link_to_btn_camera.text)
			self.stream.start(camera_num)
			self.link_to_pages.link_to_page2.link_to_btn_start_stop.text = 'Stop'
		else:
			self.stream.stop()
			self.link_to_pages.link_to_page2.link_to_btn_start_stop.text = 'Start'
			self.link_to_pages.link_to_page2.link_to_image.texture = self.main_image_texture

class Monitoring(BoxLayout):
	''' part of GUI. For details see UML diagram '''
	link_to_monitoring_file = ObjectProperty(None)
	def __init__(self, **kwargs):
		super(Monitoring, self).__init__(**kwargs)

class MonitorApp(App):
	def build(self):
		logger.info('Enter in to the build()')

		self.output_queue = Queue(maxsize=0)

		# stream
		self.stream = video_main.VideoMain()
		args = {'output_queue': self.output_queue}
		try:
			self.stream.init_tools(**args)
		except:
			logger.info('could not init_tools for stream; raise exception')
			raise ValueError('could not init_tools for stream')
		# /stream

		# container
		self.container = Container()
		args = {'stream': self.stream, 'output_queue': self.output_queue}
		self.container.init_tools(**args)
		# /container

		# camera
		self.cameras = video_main.VideoMain.get_registered_cameras()
		logger.info('registered cameras {}'.format(self.cameras))

		self.active_camera = 0 if len(self.cameras) else -1

		if self.active_camera == -1:
			logger.info('could not capture camera; raise exception')
			raise ValueError('could not capture camera')
		# /camera
	
		event = Clock.schedule_interval(self.callback_check_queue, 1 / 24.)

		if config.data[0]['monitor_on_start']:
			self.stream.start(self.active_camera)
			self.container.link_to_pages.link_to_page2.link_to_btn_start_stop.text = 'Stop'
		else:
			self.container.link_to_pages.link_to_page2.link_to_btn_start_stop.text = 'Start'

		self.icon = 'img/logo_small.png'

		logger.info('Returning build()')

		return self.container

	def on_stop(self):
		if self.container.link_to_pages.link_to_page2.link_to_btn_start_stop.text == 'Stop':
			self.stream.stop()

		encoding_file = config.data[0]['encoding_file'] \
			if config.data[0]['encoding_file'] != '' else 'encodings.pickle'
		config.data[0]['encoding_file'] = encoding_file
		album.save(config.data[0]['path_to_data_file'], encoding_file)

		config.data[0]['page'] = 'train' if self.container.link_to_pages.page == 0 else 'monitor'
		config.data[0]['monitor_on_start'] = 1 if \
			self.container.link_to_pages.link_to_page2.link_to_btn_start_stop.text == 'Stop' else 0

		logger.info('\t---\tAPPLICATION STOPPED\t---')

		return True

	def callback_check_queue(self, dt):
		try:
			self.container.transfer_frame()
		except:
			logger.info('could not call callback')
			

if __name__ == "__main__":
	logger.info('\t---\tSTART APPLICATION\t---')	# custom logger
	Logger.info('Monitor\t: START APPLICATION')		# kivy logger
	try:
		MonitorApp().run()
	except:
			logger.info('could not run Monitor application')

	config.config_save(file='config.json')