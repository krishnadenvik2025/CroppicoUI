import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-em-reset-dialog',
  templateUrl: './em-reset-dialog.component.html',
  styleUrls: ['./em-reset-dialog.component.scss']
})
export class EmResetDialogComponent implements OnInit {
  public status: 'LOADING' | 'SUCCESS' | 'FAILED' = 'LOADING';
  public statusMessage: string = 'Resetting Energy Meter...';
  public url = environment.api;

  constructor(
    private http: HttpClient,
    @Inject(MAT_DIALOG_DATA) public dialogData: any,
    public dialogRef: MatDialogRef<EmResetDialogComponent>
  ) { }

  ngOnInit(): void {
    this.resetEnergyMeter();
  }

  resetEnergyMeter() {
    this.status = 'LOADING';
    this.statusMessage = 'Resetting Energy Meter...';
    const endpoint = `${this.url}/system/EMReset`;

    this.http.get<any>(endpoint).subscribe({
      next: (res) => {
        console.log('EMReset response:', res);
        if (res?.result === true || res?.result === 'True' || res?.result === 1) {
          this.status = 'SUCCESS';
          this.statusMessage = 'Energy Meter Reset Passed';
          setTimeout(() => {
            this.dialogRef.close({ success: true, res });
          }, 1500);
        } else {
          this.status = 'FAILED';
          this.statusMessage = 'Energy Meter Reset Failed';
        }
      },
      error: (err) => {
        console.error('EMReset error:', err);
        this.status = 'FAILED';
        this.statusMessage = 'Energy Meter Reset Failed. Please try again.';
      }
    });
  }

  close() {
    this.dialogRef.close({ success: this.status === 'SUCCESS' });
  }
}
