import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CalibrationDialogComponent } from './calibration-dialog.component';

describe('CalibrationDialogComponent', () => {
  let component: CalibrationDialogComponent;
  let fixture: ComponentFixture<CalibrationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ CalibrationDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(CalibrationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
