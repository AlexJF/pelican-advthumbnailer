#!/usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals, print_function

import logging
import os
import re

from blinker import signal

from pelican import signals
from pelican.utils import mkdir_p

from bs4 import BeautifulSoup

from jinja2.ext import Extension

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
    enabled = True
except ImportError:
    logging.warning("Unable to load PIL, disabling thumbnailer")
    enabled = False

DEFAULT_THUMBNAIL_RECOGNIZER = r"(?P<basepath>.*)thumbnails/(?P<spec>[^/]+)/(?P<filename>[^/]+)$"
DEFAULT_THUMBNAIL_PATHER = "thumbnails/{spec}/{filename}"


def recognize_thumbnail(path):
    return re.match(DEFAULT_THUMBNAIL_RECOGNIZER, path)


def original_to_thumbnail_path(path, spec):
    logger.debug("ORIGINAL_TO_THUMBNAIL {} {}".format(path, spec))
    # Get original path just in case path is already a thumbnail to prevent
    # thumbnail nesting
    path = thumbnail_to_original_path(path)
    return os.path.join(os.path.dirname(path),
            DEFAULT_THUMBNAIL_PATHER.format(
                filename=os.path.basename(path),
                spec=spec))


def thumbnail_to_original_path(thumbnail_path):
    return re.sub(DEFAULT_THUMBNAIL_RECOGNIZER, r"\g<basepath>\g<filename>", thumbnail_path)


class Thumbnailer(object):
    """ Resizes based on a text specification, see readme """

    REGEX = re.compile(r'(\d+|_)x(\d+|_)(!?)')

    def __init__(self):
        pass

    def _null_resize(self, w, h, image, forced=False):
        return image

    def _exact_resize(self, w, h, image, forced=False):
        image_w, image_h = image.size

        # Do not upscale unless forced
        if image_w < w and image_h < h and not forced:
            return image

        retval = ImageOps.fit(image, (w,h), Image.ANTIALIAS)
        return retval

    def _aspect_resize(self, w, h, image, forced=False):
        retval = image.copy()
        retval.thumbnail((w, h), Image.ANTIALIAS)

        return retval

    def _resize(self, image, spec):
        resizer = self._null_resize

        # Square resize and crop
        if 'x' not in spec:
            resizer = self._exact_resize
            targetw = int(spec)
            targeth = targetw
            forced = '!' in spec
        else:
            matches = self.REGEX.search(spec)
            tmpw = matches.group(1)
            tmph = matches.group(2)
            forced = matches.group(3)

            # Full Size
            if tmpw == '_' and tmph == '_':
                targetw = image.size[0]
                targeth = image.size[1]
                resizer = self._null_resize

            # Set Height Size
            if tmpw == '_':
                targetw = image.size[0]
                targeth = int(tmph)
                resizer = self._aspect_resize

            # Set Width Size
            elif tmph == '_':
                targetw = int(tmpw)
                targeth = image.size[1]
                resizer = self._aspect_resize

            # Scale and Crop
            else:
                targetw = int(tmpw)
                targeth = int(tmph)
                resizer = self._exact_resize

        logging.debug("Using resizer {0}".format(resizer.__name__))
        return resizer(targetw, targeth, image, forced)


    def handle_path(self, path):
        logger.debug("Trying path {}".format(path))

        thumbnail_info = recognize_thumbnail(path)

        # If not a thumbnail or path already exists then do nothing
        if not thumbnail_info:
            logger.debug("Path {} does not match thumbnail pattern".format(path))
            return
        if os.path.exists(path):
            logger.debug("Path {} already exists".format(path))
            return

        logger.debug("Handling thumbnail {}".format(path))

        # If we got this far then we have a thumbnail to generate so
        # generate final directory
        thumbnail_dir = os.path.dirname(path)
        logger.debug("Thumbnail dir: {}".format(thumbnail_dir))
        if not os.path.exists(thumbnail_dir):
            logger.debug("Creating thumbnail dir: {}".format(thumbnail_dir))
            mkdir_p(thumbnail_dir)

        original_path = thumbnail_to_original_path(path)

        try:
            image = Image.open(original_path)
            thumbnail = self._resize(image, thumbnail_info.group("spec"))
            thumbnail.save(path)
            logger.info("Generated Thumbnail {}".format(os.path.basename(path)))
        except IOError as e:
            logger.error("Generating Thumbnail for {} skipped: {}".format(os.path.basename(path), str(e)))


def find_image_urls_in_file(file_path, settings):
    with open(file_path) as file_obj:
        soup = BeautifulSoup(file_obj)

        imgs = soup.find_all("img")

        urls = [img["src"] for img in imgs]

        if settings.get("ADVTHUMB_SEARCH_IMAGES_IN_ANCHORS", False):
            import urlparse, mimetypes

            links = soup.find_all("a")
            for link in links:
                if not link.has_attr("href"):
                    continue
                url = link["href"]
                maintype = mimetypes.guess_type(urlparse.urlparse(url).path)[0]
                if maintype in ("image/png", "image/jpeg", "image/gif"):
                    urls.append(url)

    return urls


class JinjaThumbnailExtension(Extension):
    def __init__(self, environment):
        super(JinjaThumbnailExtension, self).__init__(environment)

        environment.filters['thumbnail'] = original_to_thumbnail_path


def add_jinja2_ext(pelican):
    pelican.settings['JINJA_EXTENSIONS'].append(JinjaThumbnailExtension)


def find_missing_images(pelican):
    global enabled
    if not enabled:
        return

    site_url = pelican.settings["SITEURL"] + "/"
    base_dir = pelican.settings["OUTPUT_PATH"]

    logger.debug("Thumbnailer Started")

    thumbnailer = Thumbnailer()

    for dirpath, _, filenames in os.walk(base_dir):
        for filename in filenames:
            _, ext = os.path.splitext(filename)

            if not ext in [".html", ".htm"]:
                continue

            image_urls = find_image_urls_in_file(os.path.join(dirpath, filename),
                                                 pelican.settings)

            for url in image_urls:
                relative_url = url.replace(site_url, "", 1)

                # If external URL, skip
                if re.match(r"[^:]+:/", relative_url):
                    continue

                if relative_url.startswith('/'):
                    relative_url = relative_url[1:]

                relative_url_parts = relative_url.split('/')
                image_path = os.path.join(base_dir, *relative_url_parts)
                thumbnailer.handle_path(image_path)


def autostatic_path_found(sender, autostatic_path):
    if "thumb" in autostatic_path.extra:
        autostatic_path.url = original_to_thumbnail_path(
            autostatic_path.url,
            autostatic_path.extra["thumb"])


def register():
    signals.initialized.connect(add_jinja2_ext)
    signals.finalized.connect(find_missing_images)
    signal("autostatic_path_found").connect(autostatic_path_found)
