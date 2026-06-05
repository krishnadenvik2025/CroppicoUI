import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MainstatusComponent } from './mainstatus.component';

describe('MainstatusComponent', () => {
  let component: MainstatusComponent;
  let fixture: ComponentFixture<MainstatusComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MainstatusComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MainstatusComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
