import glob
import gzip
import PIL.PcfFontFile
import PIL.BdfFontFile
import sys

def convert_file(filename):
   dest_filename = filename

   if ('/' in dest_filename):
      (extra, dest_filename) = dest_filename.rsplit('/', 1)

   if ('.' in dest_filename):
      (dest_filename, extra) = dest_filename.split('.', 1)

   dest_filename = dest_filename + '.pil'

   print("Convert", filename, "to", dest_filename)

   if (filename.endswith(".gz")):
     f = gzip.open(filename, 'rb')
   else:
     f = open(filename, 'rb')

   if (".pcf" in filename):
     try:
        font_f = PIL.PcfFontFile.PcfFontFile(f)
     except IndexError:
        font_f = None

   elif (".bcf" in filename):
     font_f = PIL.BdfFontFile.BdfFontFile(f)
   else:
     print("Unknown file type for", filename)
     font_f = None

   if (font_f is not None):
     print("Converting",filename)

     font_f.save( dest_filename )
    

def main():
   files = sys.argv[1:]

   for one_arg in files:
      for one_file in glob.glob(one_arg):
        print("Working on", one_file)
        convert_file(one_file)


main()
