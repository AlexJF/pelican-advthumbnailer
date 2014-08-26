######################
pelican-advthumbnailer
######################

A thumbnail generator for `Pelican
<http://pelican.readthedocs.org/en/latest/>`_ that automatically scans
all image tags looking for missing images and creates the thumbnails
based on the filename.

Based on the existing `thumbnailer plugin
<https://github.com/getpelican/pelican-plugins/tree/master/thumbnailer>`_.

Install
=======

To install the library, you can use
`pip
<http://www.pip-installer.org/en/latest/>`_

.. code-block:: bash

    $ pip install pelican-advthumbnailer


Usage
=====

1. Update ``pelicanconf.py``:

   1. Add ``advthumbnailer`` to ``PLUGINS``.

      You should add it before any image optimization plugins.

      .. code-block:: python
          
          PLUGINS = [..., 'advthumbnailer']

2. Creating a thumbnail:

   1. Ensure original image is copied to the output folder (add to 
      ``STATIC_PATHS`` or use the `autostatic plugin
      <https://github.com/AlexJF/pelican-autostatic>`_).

      E.g: ``output/images/example.png``

   2. Add an ``<img>`` tag containing as source: ::
      
          images/thumbnails/<spec>/example.png

      Where ``<spec>`` is one of the following:

      - ``<number>``: Perform a square resize of the image to ``<number>x<number>`` pixels.
      - ``<number1>x<number2>``: Perform a scale and crop resize of the image to ``<number1>x<number2>`` pixels.
      - ``<number1>x_`` or ``_x<number2>``: Perform an aspect-preserving resize of the image enforcing the specified with or height, respectively, in pixels.

      ``<spec>`` can also be terminated with a `!` in which case upscales (e.g:
      resize 100px to 200px) will also be allowed. By default this is not the
      case.

      Example:

      .. code-block:: html

          <img src="images/thumbnails/100x_/example.png" />


   3. Upon output generation, all files are scanned for image sources and those
      matching the ``.*thumbnails/<spec>/.+`` regex are thumbnailed
      according to the ``<spec>``.


Integrations
============

pelican-autostatic
------------------
Integration with `pelican-autostatic
<https://github.com/AlexJF/pelican-autostatic>`_ is achieved by adding
an option to the ``{static ...}`` replacement.

::

    {static images/example.png thumb="100x_"}

Jinja2
------
Integration with Jinja2 is achieved via the ``thumbnail`` function.

::

    <img src="{{ SITEURL + "images/example.png" | thumbnail("100x_") }}" />

Example usage
=============
For a working example check `my site
<http://www.alexjf.net>`_ and `my site's source code
<https://github.com/AlexJF/alexjf.net>`_.
