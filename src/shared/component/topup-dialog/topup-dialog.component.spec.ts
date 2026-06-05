import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TopupDialogComponent } from './topup-dialog.component';

describe('TopupDialogComponent', () => {
  let component: TopupDialogComponent;
  let fixture: ComponentFixture<TopupDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TopupDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TopupDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
