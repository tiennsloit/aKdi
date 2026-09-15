import time
t0 = time.time()
from audiocraft.models import MusicGen
print('import OK', round(time.time()-t0,1), 's')
mg = MusicGen.get_pretrained('facebook/musicgen-small')
print('model loaded:', type(mg).__name__)
mg.set_generation_params(duration=1.0)
wav = mg.generate(['gentle acoustic guitar melody'])
print('GENERATED audio tensor shape:', tuple(wav.shape), '| sample_rate:', mg.sample_rate, '| total', round(time.time()-t0,1), 's')
print('SMOKE TEST PASSED')
