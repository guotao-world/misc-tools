# Makefile for pcm2wav
# Usage: make        # build pcm2wav
#        make clean  # remove binary

CC      = gcc
CFLAGS  = -O2 -Wall -Wextra
TARGET  = pcm2wav
SRC     = pcm2wav.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(TARGET) $(TARGET).exe

.PHONY: all clean
