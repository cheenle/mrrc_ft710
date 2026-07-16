#ifndef OPUS_BRIDGE_H
#define OPUS_BRIDGE_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Opus error codes
#define OPUS_OK 0
#define OPUS_INVALID_STATE (-1)
#define OPUS_ALLOC_FAIL (-2)
#define OPUS_BAD_ARG (-3)

// Create encoder — returns opaque handle (64-bit on arm64)
intptr_t my_create_encoder(unsigned int sampleRate, unsigned int channels, unsigned int frameSize);
void my_destroy_encoder(intptr_t encoderHandle);
int32_t my_opus_encode(intptr_t encoder, const int16_t *pcm, int32_t pcmSize, uint8_t *packet, int32_t maxPacketSize);

// Create decoder — returns opaque handle (64-bit on arm64)
intptr_t my_create_decoder(unsigned int sampleRate, unsigned int channels);
void my_destroy_decoder(intptr_t decoderHandle);

// Decode Opus to PCM
int32_t my_opus_decode(intptr_t decoder, const uint8_t *packet, int32_t packetSize, int16_t *pcm, int32_t pcmSize, int32_t decodeFEC);

#ifdef __cplusplus
}
#endif

#endif /* OPUS_BRIDGE_H */
