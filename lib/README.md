# FTDI Runtime Libraries

Place `libft4222.dylib` and `libftd2xx.dylib` in this directory to run FT4222
scope capture without depending on another wfview checkout.

Alternative overrides:

```bash
FT710_FTDI_LIB_DIR=/path/to/libs python server.py
FT710_FT4222_DYLIB=/path/libft4222.dylib FT710_FTD2XX_DYLIB=/path/libftd2xx.dylib python server.py
```
