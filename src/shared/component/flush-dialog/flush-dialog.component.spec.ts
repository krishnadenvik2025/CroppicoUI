import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FlushDialogComponent } from './flush-dialog.component';

describe('FlushDialogComponent', () => {
  let component: FlushDialogComponent;
  let fixture: ComponentFixture<FlushDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ FlushDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FlushDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
