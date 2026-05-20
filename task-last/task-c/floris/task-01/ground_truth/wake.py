from floris import FlorisModel
import yaml
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    default_path = Path('/new_home/weiyipeng/anaconda3/envs/floris/lib/python3.10/site-packages/floris/default_inputs.yaml')
    old_path = root / 'init_file' / 'two_turbine.yaml'
    cfg = yaml.safe_load(default_path.read_text())
    old = yaml.safe_load(old_path.read_text())
    cfg['name'] = old.get('name', 'TwoTurbineBase')
    cfg['farm']['layout_x'] = old['farm']['layout_x']
    cfg['farm']['layout_y'] = old['farm']['layout_y']
    name_map = {'nrel_5mw': 'nrel_5MW', 'iea_15mw': 'iea_15MW', 'iea_10mw': 'iea_10MW', 'iea_22mw': 'iea_22MW'}
    cfg['farm']['turbine_type'] = [name_map.get(t, t) if isinstance(t, str) else t for t in old['farm']['turbine_type']]
    wake_models = old.get('wake', {}).get('model_strings', {})
    cfg['wake']['model_strings']['velocity_model'] = wake_models.get('velocity_model', 'gauss')
    cfg['wake']['model_strings']['deflection_model'] = wake_models.get('deflection_model', 'gauss')
    fmodel = FlorisModel(cfg)
    fmodel.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    fmodel.run()
    turbine_powers = fmodel.get_turbine_powers() / 1000.0
    t0_kw = float(turbine_powers[0, 0])
    t1_kw = float(turbine_powers[0, 1])
    summary_text = f'{t0_kw:.6f}, {t1_kw:.6f}\n'
    (root / 'summary.txt').write_text(summary_text, encoding='utf-8')
    (root / 'ground_truth' / 'ground_truth.txt').write_text(summary_text, encoding='utf-8')

if __name__ == '__main__':
    main()
