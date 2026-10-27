# Laptop demo

A local web page that runs the real trained models: the 256 KB device model and the deferral router (as on the
ESP32-S3), and the RoBERTa-base hub (as on the Pi Zero 2 W). For every review it shows the device's answer,
whether the review is sent to the hub, the hub's answer, and the device energy that would be spent on real
hardware: processing, plus radio transmit and receive when a review is sent.

## Start it

```bash
.venv/bin/python -I demo/app.py
```

Then open http://localhost:8770. It loads in a few seconds and runs offline. The hub runs on the Mac's GPU.

The hub weights (`outputs/models/roberta_base_1m_best`, 499 MB) are downloaded from the Modal volume once:

```bash
for f in config.json tokenizer.json tokenizer_config.json model.safetensors; do .venv/bin/python -m modal volume get ai-sentiment outputs/models/roberta_base_1m/best/$f outputs/models/roberta_base_1m_best/; done
```

`.venv/bin/python -I demo/engine.py` checks the demo against the paper's saved predictions.

## Two-minute talk track

1. **The model (section 1).** "This is the model running on the device: 262,144 one-byte weights, 256 KB. With the
   router it uses 384 KB of the ESP32-S3's 512 KB. The transformer on the hub is 499 MB, about 1,300 times bigger."
2. **An easy review.** Click *Clearly positive*. "The device is almost certain, so it answers by itself. Energy:
   0.84 mJ. The radio never turns on."
3. **A hard review.** Click *Device unsure, hub fixes it*. "The device is only 59% sure, below the cut-off, so it
   sends the review. The hub corrects it to negative. That send cost 300.6 mJ, 356 times more, almost all of it
   the radio listening while the hub answers."
4. **Your own review.** Type one from the audience and press *Analyse* (or Cmd+Enter).
5. **The trade-off (section 6).** Click *Run 100 test reviews*. "Sending about 16% of reviews: accuracy close to the
   hub's, at about a fifth of the energy of sending everything." Change *Send budget* and run again to show the
   trade-off move.

Energy uses the paper's model: ESP32-S3 datasheet currents with placeholder timings (5 ms processing, 10 ms
transmit, 1 s hub wait). Hub times shown on the page are this laptop's, not the Pi's.

## Files

- `engine.py`: the models, routing thresholds (chosen on validation data, as in the paper) and the energy model
- `app.py`: a standard-library web server
- `index.html`: the page
