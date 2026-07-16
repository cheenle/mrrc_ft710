#include "OpusBridge.h"
#include <opus/opus.h>
#include <stdlib.h>

// Encoder wrapper
typedef struct {
    OpusEncoder *encoder;
} OpusEncoderWrapper;

// Decoder wrapper
typedef struct {
    OpusDecoder *decoder;
} OpusDecoderWrapper;

intptr_t my_create_encoder(unsigned int sampleRate, unsigned int channels, unsigned int frameSize) {
    OpusEncoderWrapper *wrapper = (OpusEncoderWrapper *)malloc(sizeof(OpusEncoderWrapper));
    if (!wrapper) return 0;

    wrapper->encoder = opus_encoder_create(sampleRate, channels, OPUS_APPLICATION_VOIP, NULL);
    if (!wrapper->encoder) {
        free(wrapper);
        return 0;
    }

    // Set bitrate to 28kbps for voice
    opus_encoder_ctl(wrapper->encoder, OPUS_SET_BITRATE(28000));
    opus_encoder_ctl(wrapper->encoder, OPUS_SET_VBR(0)); // CBR
    opus_encoder_ctl(wrapper->encoder, OPUS_SET_PACKET_LOSS_PERC(0));

    return (intptr_t)wrapper;
}

void my_destroy_encoder(intptr_t encoderHandle) {
    OpusEncoderWrapper *wrapper = (OpusEncoderWrapper *)encoderHandle;
    if (wrapper) {
        if (wrapper->encoder) {
            opus_encoder_destroy(wrapper->encoder);
        }
        free(wrapper);
    }
}

int32_t my_opus_encode(intptr_t encoderHandle, const int16_t *pcm, int32_t pcmSize, uint8_t *packet, int32_t maxPacketSize) {
    OpusEncoderWrapper *wrapper = (OpusEncoderWrapper *)encoderHandle;
    if (!wrapper || !wrapper->encoder) return OPUS_INVALID_STATE;

    return opus_encode(wrapper->encoder, pcm, pcmSize, packet, maxPacketSize);
}

intptr_t my_create_decoder(unsigned int sampleRate, unsigned int channels) {
    OpusDecoderWrapper *wrapper = (OpusDecoderWrapper *)malloc(sizeof(OpusDecoderWrapper));
    if (!wrapper) return 0;

    wrapper->decoder = opus_decoder_create(sampleRate, channels, NULL);
    if (!wrapper->decoder) {
        free(wrapper);
        return 0;
    }

    return (intptr_t)wrapper;
}

void my_destroy_decoder(intptr_t decoderHandle) {
    OpusDecoderWrapper *wrapper = (OpusDecoderWrapper *)decoderHandle;
    if (wrapper) {
        if (wrapper->decoder) {
            opus_decoder_destroy(wrapper->decoder);
        }
        free(wrapper);
    }
}

int32_t my_opus_decode(intptr_t decoderHandle, const uint8_t *packet, int32_t packetSize, int16_t *pcm, int32_t pcmSize, int32_t decodeFEC) {
    OpusDecoderWrapper *wrapper = (OpusDecoderWrapper *)decoderHandle;
    if (!wrapper || !wrapper->decoder) return OPUS_INVALID_STATE;

    return opus_decode(wrapper->decoder, packet, packetSize, pcm, pcmSize, decodeFEC);
}
