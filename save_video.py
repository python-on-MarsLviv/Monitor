import cv2
from imutils import resize

class Save_video():
	''' write down to file bunch of frames '''
	def __init__(self, fps=20.0, codec='MJPG'):
		self.fps = fps
		self.fourcc = cv2.VideoWriter_fourcc(*codec)

	def do_work(self, exit_queue, frame_queue, file_name_queue):
		# to save time in loop initialize variables before
		n_frames_to_write = 0
		file_name = None
		base_frame = None
		regular_frame = None
		width = None
		height = None
		writer = None

		while True:
			# handle situation to exit from while loop
			if exit_queue.qsize():
				# clean resourcess
				_ = exit_queue.get()

				n = frame_queue.qsize()
				for i in range(n):
					_ = frame_queue.get()
				#print('clean {} items on frame_queue in Save_video'.format(n))

				n = file_name_queue.qsize()
				for i in range(n):
					_,_ = file_name_queue.get()
				#print('clean {} items on file_name_queue in Save_video'.format(n))

				if writer is not None:
					writer.release()

				return
			
			# start new bunch
			if file_name_queue.qsize():
				# but before write down rest frames that belong to previous bunch
				n_frames_to_write = frame_queue.qsize()
				if n_frames_to_write:
					for i in range(n_frames_to_write):
						if writer is not None:
							writer.write(base_frame)
					if writer is not None:
						writer.release()

				# starting new bunch with given name and first(base) frame
				# each bunch has oun writer
				file_name, base_frame = file_name_queue.get()
				writer = cv2.VideoWriter(file_name, self.fourcc, self.fps, \
					(base_frame.shape[1], base_frame.shape[0]), True)
				writer.write(base_frame)

				# save size of first frame
				# it need, because user can change size during current bunch
				# but writer can work with constant size
				width = base_frame.shape[1]
				height = base_frame.shape[0]
				#continue
				
			# write all frames from queue to file
			else:
				if writer is not None:
					n_frames_to_write = frame_queue.qsize()
					for i in range(n_frames_to_write):
						regular_frame = frame_queue.get()
						if regular_frame.shape[1] == width:
							writer.write(regular_frame)
						else:
							regular_frame = resize(regular_frame, width=width)
							writer.write(regular_frame)
