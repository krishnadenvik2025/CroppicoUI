import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit, Pipe, PipeTransform } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ApiService } from 'src/core/api-service/api.service';
import { APIS } from 'src/shared/model/api.model';

@Pipe({ name: 'safeUrl' })
export class SafeUrlPipe implements PipeTransform {
  constructor (private sanitizer: DomSanitizer) { }

  transform (url: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}
@Component({
  selector: 'app-guide',
  templateUrl: './guide.component.html',
  styleUrls: ['./guide.component.css']
})
export class GuideComponent implements OnInit {

  video_url: string = '';
  pdf_url: any = '';
  video_list: any[] = [];
  pdf_list: any[] = [];


  public media_type = "VIDEO";
  constructor (public dialogRef: MatDialogRef<GuideComponent>,
    @Inject(MAT_DIALOG_DATA) public dialogData: any, private apiService: ApiService, private http: HttpClient, private sanitizer: DomSanitizer) { }

  ngOnInit (): void {

    this.apiService.httpGet(APIS.GETGUIDE).subscribe((res) => {
      if (res) {
        this.video_list = res.Video;
        this.video_url = res.Video[0]?.url;
        this.pdf_list = res.pdf;
        console.log("RES", res);
      }

    });
  }


  showVideo (video: any) {
    this.media_type = 'VIDEO';
    this.video_url = video.url;

  }
  showPdf (pdf: any) {
    this.media_type = 'PDF';
    this.pdf_url = this.sanitizer.bypassSecurityTrustResourceUrl(pdf.url + '#toolbar=0');
    console.log("URL", this.pdf_url);


  }
}
