CC=g++
LIBS=$(XED_ROOT)/lib/libxed.a
CFLAGS=-I. -I$(XED_ROOT)/include -pedantic -Wall \
	   -Wformat-security -Wunused -Werror -Wno-long-long \
	   -Wno-unknown-pragmas -fmessage-length=0 -pipe \
	   -fomit-frame-pointer -fno-exceptions -Wwrite-strings \
	   -Wredundant-decls

ODIR=obj
BIN=decoder

all: decoder

decoder: $(ODIR)/hex_decoder.o
	$(CC) -o $@ $^ $(LIBS)

$(ODIR)/hex_decoder.o: hex_decoder.cpp
	$(CC) -c -o $@ $< $(CFLAGS)

.PHONY: clean

clean:
	rm $(ODIR)/* $(BIN)
