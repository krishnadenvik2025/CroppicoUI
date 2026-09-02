import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SettingsComponent } from './settings.component';

describe('SettingsComponent', () => {
  let component: SettingsComponent;
  let fixture: ComponentFixture<SettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should switch to API mode without requiring a device id', () => {
    component.onOaqOptionSelected('API');

    expect(component.oaqSelection).toBe('API');
    expect(component.oaqDeviceId).toBe('');
  });

  it('should store the entered sensor device id', () => {
    spyOn(window, 'prompt').and.returnValue('ABC123');

    component.onOaqOptionSelected('Sensor');

    expect(component.oaqSelection).toBe('Sensor');
    expect(component.oaqDeviceId).toBe('ABC123');
  });
});
