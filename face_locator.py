import pickle
import cv2
import dlib
import face_recognition
from time import perf_counter
import multiprocessing
from os import getpid

# function detecting faces on picture and tracking them
# if person in album - inform name

# function designed to work in separate Process or Thread
# communication with caller with Queues:
#			quit_queue - transfer information to quit
#			input_queue - transfer input information
#			ouput_queue - transfer ouput information
#			tracking_names_queue - transfer current names from caller
# and lists: names_known - list of known names in album
#			encodings_known - list encoded information for each name
#			names_new, encodings_new - reserved for planned feature

def face_locator(names_known, encodings_known, names_new, encodings_new, \
		input_queue, ouput_queue, quit_queue, tracking_names_queue):
	# to save time in loops initialize variables before
	base_frame = None; regular_frame = None; p_time = None
	quit = False
	boxes = None; encodings = None; trackers = None; names = None
	encoding = None; box = None
	matched_names = None; probabilities = None; found = None
	name = None; encod = None
	matches = None
	startX = None; startY = None; endX = None; endY = None;
	rect = None; tracker = None
	m = None; max_idxs = None; temp_names = None

	to_mark = 1

	tracking_names = []
	#print('in to face_locator Process   pid:', getpid())

	# function work until will get True in quit_queue
	while True:
		# handle situation to exit from while loop
		if quit_queue.qsize():
			# clean queues
			_ = quit_queue.get()
			
			q_size = input_queue.qsize()
			for i_empty in range(q_size):
				_,_,_ = input_queue.get()
			#print('clean {} items on input_queue pid: {}'.format(q_size, getpid()))

			q_size = ouput_queue.qsize()
			for i_empty in range(q_size):
				_,_,_,_ = ouput_queue.get()
			#print('clean {} items on output_queue pid: {}'.format(q_size, getpid()))
			#print('out 1 of face_locator Process pid:', getpid())
			return

		trackers = []; names = []

		# if available frame - make it base frame and track other frames on input_queue
		if input_queue.qsize():
			#print('started base frame with {} frame. Process pid: {}'.format(input_queue.qsize(), getpid()))
			tic = perf_counter()
			base_frame, to_mark, p_time = input_queue.get()
			base_frame = cv2.cvtColor(base_frame, cv2.COLOR_BGR2RGB)

			boxes = face_recognition.face_locations(base_frame, number_of_times_to_upsample=1, model='hog')
			encodings = face_recognition.face_encodings(base_frame, boxes)

			# go througth all boxes find name and start tracker
			for (encoding, box) in zip(encodings, boxes):
				startX = box[3]; startY = box[0]; endX = box[1]; endY = box[2]
				rect = dlib.rectangle(startX, startY, endX, endY)
				tracker = dlib.correlation_tracker()
				tracker.start_track(base_frame, rect)
				matched_names = [] # for current encoding gather all matched names with different probabilities
				probabilities = []
				temp_names = ''
				found = False

				# to speed up algorithm in first place compare encodigs with current names
				if tracking_names_queue.qsize():
					tracking_names = tracking_names_queue.get()
				for name in tracking_names:
					idx = names_known.index(name)
					matches = face_recognition.compare_faces(encodings_known[idx], encoding, tolerance=.6)
					if any(matches):
						names.append(name)
						trackers.append(tracker)
						if to_mark:
							cv2.rectangle(base_frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
							cv2.putText(base_frame, name, (startX, startY - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
						found = True
						break

				if found:		# jump to next encoding
					found = False
					continue

				# searching in rest names
				for (name, encod) in zip(names_known, encodings_known):
					# check if we already compared with this name above
					if name in tracking_names:
						continue

					matches = face_recognition.compare_faces(encod, encoding, tolerance=.6)
					if all(matches) and len(matches) > 1:
						names.append(name)
						trackers.append(tracker)
						if to_mark:
							cv2.rectangle(base_frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
							cv2.putText(base_frame, name, (startX, startY - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
						found = True
						break
					elif all(matches) and len(matches) == 1:
						matched_names.append(name)
						probabilities.append(.5)
						continue
					elif any(matches) and len(matches) > 1:
						matched_names.append(name)
						probabilities.append(sum(matches) / len(matches))
				if found:		# jump to next encoding
					found = False
					continue
				if not len(matched_names):			# current encoding are undefined
					names.append('underfined')
					trackers.append(tracker)
					continue
				m = max(probabilities)				# case when couple names with same probability
				max_idxs = [i for i, j in enumerate(probabilities) if j == m]
				for i in max_idxs:
					temp_names += matched_names[i]
					temp_names += '_or_'
				if temp_names.endswith('_or_'):
					temp_names = temp_names[0:-4]

				names.append(temp_names)
				trackers.append(tracker)
				if to_mark:
					cv2.rectangle(base_frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
					cv2.putText(base_frame, temp_names, (startX, startY - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

			base_frame = cv2.cvtColor(base_frame, cv2.COLOR_RGB2BGR)
			ouput_queue.put((base_frame, names, 0, p_time));#print('names:', names, ' Process pid:', getpid())
			
			toc = perf_counter()
			time_locate = toc - tic
			#print('time to locate', time_locate, ' Process pid:', getpid())

			# tracking all rest frames
			tic = perf_counter()
			#print('regular frames:', input_queue.qsize(), ' pid:', getpid())
			while input_queue.qsize():
				#print('while input_queue.qsize():', input_queue.qsize(), ' pid:', getpid())
				# handle situation to exit from while loop
				if quit_queue.qsize():
					# clean queues
					_ = quit_queue.get()
					
					q_size = input_queue.qsize()
					for i_empty in range(q_size):
						_,_,_ = input_queue.get()
					#print('clean {} items on input_queue pid: {}'.format(q_size, getpid()))

					q_size = ouput_queue.qsize()
					for i_empty in range(q_size):
						_,_,_,_ = ouput_queue.get()
					#print('clean {} items on output_queue pid: {}'.format(q_size, getpid()))
					#print('out 2 of face_locator Process pid:', getpid())
					return

				regular_frame, to_mark, p_time = input_queue.get()
				if len(names):
					regular_frame = cv2.cvtColor(regular_frame, cv2.COLOR_BGR2RGB)

					for (tracker, name) in zip(trackers, names):
						tracker.update(regular_frame)
						if to_mark:
							pos = tracker.get_position()
							startX = int(pos.left())
							startY = int(pos.top())
							endX = int(pos.right())
							endY = int(pos.bottom())
							cv2.rectangle(regular_frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
							cv2.putText(regular_frame, name, (startX, startY + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
					regular_frame = cv2.cvtColor(regular_frame, cv2.COLOR_RGB2BGR)

				# if it is the last frame
				# then it transfer to main Process with frame_koef
				# calculate this value are possible only after curren while loop
				if input_queue.qsize():
					ouput_queue.put((regular_frame, names, 0, p_time))

			toc = perf_counter()
			time_track = toc - tic
			frame_koef = 1.4 - time_track / time_locate
			ouput_queue.put((regular_frame, names, frame_koef, p_time)) # transfer to main Process last frame with frame_koef
			#print('time to track', time_track, ' Process pid:', getpid())

	#print('out of while', ' Process pid:', getpid())



