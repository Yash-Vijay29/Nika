#include <chrono>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>

#include "piper.hpp"

using namespace std;

struct RunConfig {
  filesystem::path encoderPath;
  filesystem::path decoderPath;
  filesystem::path modelConfigPath;
  optional<piper::SpeakerId> speakerId;
  optional<float> noiseScale;
  optional<float> lengthScale;
  optional<float> noiseW;
  optional<float> sentenceSilenceSeconds;
  optional<filesystem::path> eSpeakDataPath;
  string accelerator = "";
};

void parseArgs(int argc, char *argv[], RunConfig &runConfig);

int main(int argc, char *argv[]) {
  // Set logging to errors only for cleaner Python integration
  spdlog::set_level(spdlog::level::err);
  
  RunConfig runConfig;
  parseArgs(argc, argv, runConfig);

  piper::PiperConfig piperConfig;
  piper::Voice voice;

  // Load voice model
  loadVoice(piperConfig, "", runConfig.encoderPath.string(), runConfig.decoderPath.string(),
            runConfig.modelConfigPath.string(), voice, runConfig.speakerId,
            runConfig.accelerator);
  
  // Get executable path for espeak-ng-data location
  auto exePath = filesystem::canonical("/proc/self/exe");

  if (voice.phonemizeConfig.phonemeType == piper::eSpeakPhonemes) {
    if (runConfig.eSpeakDataPath) {
      piperConfig.eSpeakDataPath = runConfig.eSpeakDataPath.value().string();
    } else {
      piperConfig.eSpeakDataPath =
          std::filesystem::absolute(
              exePath.parent_path().append("espeak-ng-data"))
              .string();
    }
  } else {
    piperConfig.useESpeak = false;
  }

  piper::initialize(piperConfig);

  // Apply synthesis settings
  if (runConfig.noiseScale) {
    voice.synthesisConfig.noiseScale = runConfig.noiseScale.value();
  }
  if (runConfig.lengthScale) {
    voice.synthesisConfig.lengthScale = runConfig.lengthScale.value();
  }
  if (runConfig.noiseW) {
    voice.synthesisConfig.noiseW = runConfig.noiseW.value();
  }
  if (runConfig.sentenceSilenceSeconds) {
    voice.synthesisConfig.sentenceSilenceSeconds =
        runConfig.sentenceSilenceSeconds.value();
  }

  // Process text from stdin, output raw audio to stdout
  string line;
  piper::SynthesisResult result;
  while (getline(cin, line)) {
    vector<int16_t> audioBuffer;
    
    // Callback to stream audio as it's generated
    auto audioCallback = [&audioBuffer]() {
      cout.write((const char *)audioBuffer.data(),
                 sizeof(int16_t) * audioBuffer.size());
      cout.flush();
    };
    
    piper::textToAudio(piperConfig, voice, line, audioBuffer, result,
                       audioCallback);
  }

  piper::terminate(piperConfig);
  return EXIT_SUCCESS;
}

void parseArgs(int argc, char *argv[], RunConfig &runConfig) {
  optional<filesystem::path> modelConfigPath;

  for (int i = 1; i < argc; i++) {
    std::string arg = argv[i];

    if (arg == "--encoder" && i + 1 < argc) {
      runConfig.encoderPath = filesystem::path(argv[++i]);
    } else if (arg == "--decoder" && i + 1 < argc) {
      runConfig.decoderPath = filesystem::path(argv[++i]);
    } else if ((arg == "-c" || arg == "--config") && i + 1 < argc) {
      modelConfigPath = filesystem::path(argv[++i]);
    } else if ((arg == "-s" || arg == "--speaker") && i + 1 < argc) {
      runConfig.speakerId = (piper::SpeakerId)stol(argv[++i]);
    } else if (arg == "--noise_scale" && i + 1 < argc) {
      runConfig.noiseScale = stof(argv[++i]);
    } else if (arg == "--length_scale" && i + 1 < argc) {
      runConfig.lengthScale = stof(argv[++i]);
    } else if (arg == "--noise_w" && i + 1 < argc) {
      runConfig.noiseW = stof(argv[++i]);
    } else if (arg == "--sentence_silence" && i + 1 < argc) {
      runConfig.sentenceSilenceSeconds = stof(argv[++i]);
    } else if (arg == "--espeak_data" && i + 1 < argc) {
      runConfig.eSpeakDataPath = filesystem::path(argv[++i]);
    } else if (arg == "--accelerator" && i + 1 < argc) {
      runConfig.accelerator = argv[++i];
    } else if (arg == "-h" || arg == "--help") {
      cerr << "Usage: " << argv[0] << " [options]" << endl;
      cerr << "Options:" << endl;
      cerr << "  --encoder FILE     Path to encoder model" << endl;
      cerr << "  --decoder FILE     Path to decoder model" << endl;
      cerr << "  -c, --config FILE  Path to model config JSON" << endl;
      cerr << "  -s, --speaker NUM  Speaker ID (default: 0)" << endl;
      cerr << "  --accelerator STR  Accelerator (e.g., 'cuda')" << endl;
      cerr << "  --espeak_data DIR  Path to espeak-ng-data" << endl;
      cerr << "  -h, --help         Show this help" << endl;
      exit(0);
    }
  }

  // Verify required arguments
  if (!filesystem::exists(runConfig.encoderPath)) {
    throw runtime_error("Encoder model file doesn't exist");
  }
  if (!filesystem::exists(runConfig.decoderPath)) {
    throw runtime_error("Decoder model file doesn't exist");
  }
  if (!modelConfigPath) {
    throw runtime_error("Model config file must be provided");
  }
  runConfig.modelConfigPath = modelConfigPath.value();
  if (!filesystem::exists(runConfig.modelConfigPath)) {
    throw runtime_error("Model config doesn't exist");
  }
}
