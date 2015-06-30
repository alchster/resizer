#!/usr/bin/env python2

from flask import Flask, request, send_file, abort
from io import BytesIO
from PIL import Image
import numpy
from werkzeug.contrib.fixers import LighttpdCGIRootFix, HeaderRewriterFix
import memcache

img_dir = '/var/www/static/'

app = Flask(__name__)
app.wsgi_app = LighttpdCGIRootFix(app.wsgi_app)
app.wsgi_app = HeaderRewriterFix(app.wsgi_app, remove_headers=['Date'], add_headers=[('X-Powered-By', 'WSGI'), ('Server', 'Noname Server')])

memcached = memcache.Client(['127.0.0.1:11211'])

@app.route('/resize', methods = [ 'GET' ])
def api_resize():
	try:
		img_file_name = request.args.get('img')
		target_width = float(request.args.get('w'))
		memcached_index = (':'.join((img_file_name.split('/')[-1], str(int(target_width))))).encode('utf-8')
		img_io = BytesIO()
		img_bin = memcached.get(memcached_index)
		if img_bin:
			img_io.write(img_bin)
		else:
			image = Image.open(img_dir + img_file_name)
			mul = target_width/image.size[0]
			method = Image.ANTIALIAS
			if mul > 1:
				method = Image.NEAREST
			if img_file_name.endswith('.png'):
				image = image.convert('RGBA')
				premult = numpy.fromstring(image.tostring(), dtype=numpy.uint8)
				alphaLayer = premult[3::4] / 255.0
				premult[::4] *= alphaLayer
				premult[1::4] *= alphaLayer
				premult[2::4] *= alphaLayer
				image = Image.fromstring("RGBA", image.size, premult.tostring())
			image = image.resize((int(target_width), int(image.size[1]*mul)), method)
			image.save(img_io, 'JPEG', quality=90)
			img_io.seek(0)
			img_bin = img_io.read()
			memcached.set(memcached_index, img_bin)
		img_io.seek(0)
		return send_file(img_io, mimetype='image/jpeg')
	except Exception as e:
		print e
		pass
	return abort(404)

if __name__ == '__main__':
	app.run(debug=True, port=9000)
